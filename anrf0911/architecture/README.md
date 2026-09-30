# 架构流图

http://127.0.0.1:8000/architecture/

蓝色 = 已实现（Day01～03）。橙色虚线 = Day04 待敲。

Day03：HTTP 收消息，留下 `COLLECTING`，立刻返回。  
Day04：后台 Worker 领取到期轮次 → 调 AI :8002 → 把 `role=ai` 消息写回库。

今天最简路径跳过：写订单两阶段、转人工、WebSocket outbox。
