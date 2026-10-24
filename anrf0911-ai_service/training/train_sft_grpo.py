"""在单卡 32GB 上先 SFT，再 GRPO。

AutoDL 上从 anrf0911-ai_service 目录执行：

    python training/train_sft_grpo.py --stage prepare
    python training/train_sft_grpo.py --stage sft
    python training/train_sft_grpo.py --stage grpo
    python training/train_sft_grpo.py --stage merge

V100 使用默认 fp16。显存不够时加 --num-generations 2，或先只跑 sft。
"""

from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.data import build_samples, write_jsonl
from training.format import render_messages


DATA_PATH = ROOT / "training" / "data" / "support.jsonl"
OUTPUT_DIR = ROOT / "training" / "outputs"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["prepare", "sft", "grpo", "merge", "all"], default="all")
    parser.add_argument("--model", default="unsloth/Qwen2.5-7B-Instruct")
    parser.add_argument("--dtype", choices=["fp16", "bf16"], default="fp16")
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--grpo-steps", type=int, default=300)
    parser.add_argument("--no-vllm", action="store_true")
    return parser.parse_args()


def prepare() -> None:
    count = write_jsonl(DATA_PATH)
    print(f"wrote {count} samples to {DATA_PATH}")


def sft_rows(tokenizer) -> list[dict]:
    rows = []
    for sample in build_samples():
        rows.append({
            "text": render_messages(sample.messages, tokenizer=tokenizer),
        })
    return rows


def grpo_rows(tokenizer) -> list[dict]:
    rows = []
    for sample in build_samples():
        if sample.task != "answer":
            continue
        prompt = render_messages(
            sample.messages[:-1],
            add_generation_prompt=True,
            tokenizer=tokenizer,
        )
        rows.append({
            "prompt": prompt,
            "question": sample.question,
            "tool_evidence": sample.to_row()["tool_evidence"],
        })
    return rows


def load_model(model_name: str, max_seq_length: int, dtype: str, fast_inference: bool, adapter: str | None):
    import torch
    from unsloth import FastLanguageModel

    dtype_value = torch.float16 if dtype == "fp16" else torch.bfloat16
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter or model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        dtype=dtype_value,
        fast_inference=fast_inference,
    )
    if adapter is None:
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            lora_alpha=16,
            lora_dropout=0,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            use_gradient_checkpointing="unsloth",
        )
    return model, tokenizer


def train_sft(args) -> None:
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel

    model, tokenizer = load_model(args.model, args.max_seq_length, args.dtype, False, None)
    dataset = Dataset.from_list(sft_rows(tokenizer))
    output = OUTPUT_DIR / "sft"
    trainer_kwargs = {
        "model": model,
        "train_dataset": dataset,
        "args": SFTConfig(
            output_dir=str(output),
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            num_train_epochs=2,
            learning_rate=2e-4,
            logging_steps=5,
            save_strategy="epoch",
            max_length=args.max_seq_length,
            dataset_text_field="text",
            packing=False,
        ),
    }
    try:
        trainer = SFTTrainer(processing_class=tokenizer, **trainer_kwargs)
    except TypeError:
        trainer = SFTTrainer(tokenizer=tokenizer, **trainer_kwargs)
    trainer.train()
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    FastLanguageModel.for_inference(model)
    del trainer, model
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except ImportError:
        pass
    print(f"SFT adapter saved to {output}")


def train_grpo(args) -> None:
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer

    adapter = OUTPUT_DIR / "sft"
    if not adapter.exists():
        raise SystemExit("先运行 --stage sft，GRPO 从 SFT 适配器继续。")
    model, tokenizer = load_model(
        args.model,
        args.max_seq_length,
        args.dtype,
        fast_inference=not args.no_vllm,
        adapter=str(adapter),
    )
    dataset = Dataset.from_list(grpo_rows(tokenizer))
    output = OUTPUT_DIR / "grpo"
    grpo_args = dict(
        output_dir=str(output),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_generations=args.num_generations,
        max_prompt_length=1536,
        max_completion_length=384,
        learning_rate=5e-6,
        beta=0.04,
        temperature=0.8,
        max_steps=args.grpo_steps,
        logging_steps=1,
        save_steps=50,
    )
    if not args.no_vllm:
        grpo_args["use_vllm"] = True
        grpo_args["vllm_gpu_memory_utilization"] = 0.5
    try:
        config = GRPOConfig(**grpo_args)
    except TypeError:
        grpo_args.pop("use_vllm", None)
        grpo_args.pop("vllm_gpu_memory_utilization", None)
        config = GRPOConfig(**grpo_args)
    trainer_kwargs = {
        "model": model,
        "reward_funcs": [reward_func],
        "train_dataset": dataset,
        "args": config,
    }
    try:
        trainer = GRPOTrainer(processing_class=tokenizer, **trainer_kwargs)
    except TypeError:
        trainer = GRPOTrainer(tokenizer=tokenizer, **trainer_kwargs)
    trainer.train()
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    print(f"GRPO adapter saved to {output}")


def reward_func(completions, tool_evidence=None, question=None, **kwargs):
    from training.reward import support_reward

    return support_reward(
        completions,
        tool_evidence=tool_evidence,
        question=question,
        **kwargs,
    )


def merge_adapter(args) -> None:
    from unsloth import FastLanguageModel

    adapter = OUTPUT_DIR / "grpo"
    if not adapter.exists():
        adapter = OUTPUT_DIR / "sft"
    if not adapter.exists():
        raise SystemExit("没有可合并的适配器。")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(adapter),
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
    )
    merged = OUTPUT_DIR / "merged"
    model.save_pretrained_merged(str(merged), tokenizer, save_method="merged_16bit")
    print(f"merged model saved to {merged}")


def main() -> None:
    args = parse_args()
    if args.stage in {"prepare", "all"}:
        prepare()
    if args.stage == "prepare":
        return
    if args.stage in {"sft", "all"}:
        train_sft(args)
    if args.stage in {"grpo", "all"}:
        train_grpo(args)
    if args.stage in {"merge", "all"}:
        merge_adapter(args)


if __name__ == "__main__":
    main()
