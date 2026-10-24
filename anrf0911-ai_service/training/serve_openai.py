"""把合并后的客服模型暴露成 OpenAI 兼容接口，替换原来的 llm_base_url。

启动：

    python training/serve_openai.py --model-path training/outputs/merged

AI Service 的 .env：

    LLM_PROVIDER=local
    LOCAL_MODEL_BASE_URL=http://127.0.0.1:8003/v1
    LOCAL_SERVED_MODEL=customer-support-grpo
    LLM_API_KEY=local
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

from training.format import TOOL_CALL_PATTERN, extract_payload, render_messages


app = FastAPI(title="Customer Support Model")
generate_lock = threading.Lock()
state: dict = {}


class ChatRequest(BaseModel):
    model: str = "customer-support-grpo"
    messages: list[dict]
    tools: list[dict] | None = None
    temperature: float = 0
    max_tokens: int = 384
    stream: bool = False


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "local"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=str(ROOT / "training" / "outputs" / "merged"))
    parser.add_argument("--served-model-name", default="customer-support-grpo")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--dtype", choices=["fp16", "bf16"], default="fp16")
    parser.add_argument("--api-key", default="")
    return parser.parse_args()


def load_model(path: str, dtype_name: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = torch.float16 if dtype_name == "fp16" else torch.bfloat16
    tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        path,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def parse_tool_calls(text: str, tools: list[dict] | None) -> list[dict]:
    calls = []
    for matched in TOOL_CALL_PATTERN.finditer(text):
        payload = extract_payload(matched.group(1))
        if isinstance(payload, dict) and payload.get("name"):
            calls.append(payload)
    if calls:
        return [openai_tool_call(item) for item in calls]

    payload = extract_payload(text)
    if not isinstance(payload, dict):
        return []
    if payload.get("name") and "arguments" in payload:
        return [openai_tool_call(payload)]
    if "reply_type" in payload and tool_names(tools).intersection({"AgentOutput"}):
        return [openai_tool_call({"name": "AgentOutput", "arguments": payload})]
    return []


def tool_names(tools: list[dict] | None) -> set[str]:
    names = set()
    for tool in tools or []:
        function = tool.get("function") or tool
        if function.get("name"):
            names.add(function["name"])
    return names


def openai_tool_call(payload: dict) -> dict:
    arguments = payload.get("arguments") or {}
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments, ensure_ascii=False)
    return {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {
            "name": payload["name"],
            "arguments": arguments,
        },
    }


def generate(messages: list[dict], temperature: float, max_tokens: int) -> tuple[str, int, int]:
    import torch

    model = state["model"]
    tokenizer = state["tokenizer"]
    prompt = render_messages(
        messages,
        add_generation_prompt=True,
        tokenizer=tokenizer,
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    do_sample = temperature > 0
    generate_kwargs = {
        "max_new_tokens": max_tokens,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if do_sample:
        generate_kwargs["temperature"] = temperature
    with generate_lock, torch.inference_mode():
        output = model.generate(**inputs, **generate_kwargs)
    prompt_tokens = int(inputs["input_ids"].shape[-1])
    completion_ids = output[0][prompt_tokens:]
    text = tokenizer.decode(completion_ids, skip_special_tokens=True)
    text = text.split("<|im_end|>")[0].strip()
    return text, prompt_tokens, int(completion_ids.shape[-1])


def check_key(authorization: str | None) -> None:
    expected = state.get("api_key") or ""
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/health")
def health():
    return {"status": "ok", "model": state.get("served_name", "")}


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [ModelCard(id=state["served_name"]).model_dump()],
    }


@app.post("/v1/chat/completions")
def chat_completions(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    check_key(authorization)
    if request.stream:
        raise HTTPException(status_code=400, detail="这个本地接口不开启流式输出")
    text, prompt_tokens, completion_tokens = generate(
        request.messages,
        request.temperature,
        request.max_tokens,
    )
    tool_calls = parse_tool_calls(text, request.tools)
    message = {"role": "assistant", "content": None if tool_calls else text}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model or state["served_name"],
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "tool_calls" if tool_calls else "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def main() -> None:
    args = parse_args()
    model_path = Path(args.model_path)
    if not model_path.exists():
        raise SystemExit(f"找不到模型目录：{model_path}")
    model, tokenizer = load_model(str(model_path), args.dtype)
    state.update({
        "model": model,
        "tokenizer": tokenizer,
        "served_name": args.served_model_name,
        "api_key": args.api_key,
    })
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
