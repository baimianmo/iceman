# IceMan 客户关怀助手

本项目实现一个类似 OpenClaw 的客户关怀系统：接入飞书，实现对话内的语义理解、客户画像查询以及祝福贺卡生成与发送。

## 1. 程序说明（程序可以做什么）

- 在飞书聊天窗口与机器人对话，自动识别意图（如生日关怀、节日关怀、喜事庆祝等）。
- 根据用户输入提取客户姓名（识别“张先生/张女士”等称呼），查询或生成该客户的私行画像（模拟）。
- 基于画像与意图生成合适的祝福文案，并用 Pillow 生成贺卡图片。
- 将“客户画像（JSON 卡片）”与“贺卡图片（卡片）”发送至当前飞书对话。
- 支持本地调试与 CLI 自验证，DeepSeek 接口可选（未配置则自动回退为 Mock 文案）。

交互效果（默认顺序）：
1) 先发送“👤 客户画像数据”（JSON 代码块卡片）；
2) 再发送“🎂 祝福贺卡”（仅含图片的卡片）。

## 2. 启动方式

- 前置准备（飞书后台）：
  - 在开发者后台创建应用，开通权限：`im:message:send_as_bot`、`im:image:upload`；发布版本。
  - 事件订阅启用并勾选：`im.message.receive_v1`。

- 启动服务：
  1) 设置环境变量（在同一终端执行）：
     ```bash
     export FEISHU_APP_ID="cli_xxxxxxxxxx"
     export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
     # 可选：DeepSeek，如不设置则自动使用 Mock
     # export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
     ```
  2) 启动 Flask 服务（默认端口 8080，避开 macOS AirPlay 占用的 5000）：
     ```bash
     python3 feishu_server.py
     ```
  3) 开启内网穿透（无需注册）：
     ```bash
     npm install -g localtunnel
     lt --port 8080
     ```
  4) 将 localtunnel 输出的公网地址追加 `/webhook/event` 配置到飞书“事件订阅 → 请求地址”并验证通过。
  5) 在飞书中与应用对话发送：
     - 示例：“给张先生发个生日祝福”
     - 示例：“王先生的儿子考上了清华大学”

- 本地快速验证（不依赖飞书）：
  ```bash
  python3 -c "from agents import main_agent; r = main_agent.run_and_return('王先生的儿子考上了清华大学'); import json; print(json.dumps(r, ensure_ascii=False, indent=2))"
  ```
  该命令会打印结构化结果并在 `output_cards/` 生成图片文件。

## 3. 实现原理

- 架构与调用链
  - 飞书 → Flask Webhook（`/webhook/event`）→ 异步处理线程
  - 异步线程调用主 Agent：`MainAgent.run_and_return(text)`
  - MainAgent：
    - 规则/关键词识别意图（生日/节日/喜事/其他）；
    - 从文本中提取姓名（支持“张先生/张女士”）；
    - 调用 Skill 查询/生成客户画像（Faker 模拟、性别随称呼一致）；
    - 调用子 Agent（Birthday/Holiday/Celebration）基于画像生成文案；
    - 使用 Pillow 生成贺卡图片；
    - 返回结构化结果：`{ profile, blessing, image_path, text }`。
  - 飞书发送层：
    - 先发送“客户画像 JSON 卡片”；
    - 再上传图片并发送“图片卡片”。

- 幂等与重试处理
  - 在 Webhook 处理函数中加入 `message_id` 去重缓存（定长窗口），忽略飞书可能的重复推送；
  - 过滤非用户消息（避免机器人自发消息回环）。

## 4. 依赖组件

- Python 3.9+
  - Flask（Webhook 服务）
  - requests（HTTP 调用 Feishu/OpenAPI）
  - Pillow（贺卡图片生成）
  - Faker（私行客户画像模拟）
- Node.js（可选，用于内网穿透）
  - localtunnel（`npm i -g localtunnel`）
- 可选：DeepSeek（或兼容 OpenAI 接口的模型），通过 `DEEPSEEK_API_KEY` 启用；未设置将使用 Mock。

## 5. 安装方式

1) Python 依赖安装（建议虚拟环境）：
```bash
python3 -m venv venv && source venv/bin/activate
pip install flask requests pillow faker
```

2) 可选：安装 localtunnel（推荐）：
```bash
npm install -g localtunnel
```

3) 环境变量设置：
```bash
export FEISHU_APP_ID="cli_xxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# 可选：DeepSeek
# export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

4) 运行：
```bash
python3 feishu_server.py
lt --port 8080
```
在飞书后台配置 `https://<你的域名>.loca.lt/webhook/event` 并验证，通过后即可以与机器人对话完成“画像 + 贺卡”闭环。

---

### 目录结构（简要）

```
iceman/
├─ feishu_server.py       # 飞书 Webhook 服务（异步处理、幂等、卡片/图片发送）
├─ agents.py              # MainAgent + 子 Agent（生日/节日/喜事），结构化返回
├─ skills.py              # 画像查询与贺卡图片生成（Pillow）
├─ profile_service.py     # Faker 模拟私行客户画像（称呼 → 性别一致）
├─ llm_client.py          # LLM 客户端（DeepSeek，未配置则 Mock）
├─ output_cards/          # 自动生成的贺卡图片输出目录
└─ README.md
```

### 常见问题

- “没有响应”：确认 localtunnel 正在运行、飞书事件订阅地址指向 `/webhook/event` 且验证通过；确认应用已加入当前会话并发布了权限变更；群聊中请 @ 应用。
- “重复回复”：代码已加入 message_id 去重；如仍出现，请截图日志中的 `message_id` 并反馈。

