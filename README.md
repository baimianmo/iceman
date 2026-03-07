# IceMan 客户关怀助手

本项目实现一个类似 OpenClaw 的客户关怀系统：接入飞书，实现对话内的语义理解、客户画像查询以及祝福贺卡生成与发送。

## 1. 程序说明（程序可以做什么）

- 在飞书聊天窗口与机器人对话，自动识别意图（如生日关怀、节日关怀、喜事庆祝等）。
- 根据用户输入提取客户姓名（识别“张先生/张女士”等称呼），查询或生成该客户的私行画像（模拟）。
- 基于画像与意图生成合适的祝福文案，并用 Pillow 生成贺卡图片。
- 将“客户画像（JSON 卡片）”与“贺卡图片（卡片）”发送至当前飞书对话。
- 支持本地调试与 CLI 自验证；模型后端可选 DeepSeek 或本地 Ollama（未配置时自动回退 Mock）。
- 技能系统可扩展：支持 skills.md 注册表（大模型可读）、按需加载、以及通过 manifest 在线安装外部技能；兼容 HTTP 类型技能描述。

交互效果（默认顺序）：
1) 先发送“👤 客户画像数据”（JSON 代码块卡片）；
2) 再发送“🎂 祝福贺卡”（仅含图片的卡片）。

## 2. 启动方式

- 前置准备（飞书后台）：
  - 在开发者后台创建应用，开通权限：`im:message:send_as_bot`、`im:image:upload`；发布版本。
  - 事件订阅启用并勾选：`im.message.receive_v1`。

- 前置准备（企业微信后台）：
  - 创建企业微信“自建应用”，记录 `CorpID`、`CorpSecret`、`AgentID`。
  - 在“接收消息服务器配置”中，开发阶段可先用 GET `echostr` 校验通过（生产需启用加密并校验签名/解密）。

- 启动服务：
  1) 设置环境变量（在同一终端执行）：
     ```bash
     export FEISHU_APP_ID="cli_xxxxxxxxxx"
     export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
     # 可选：飞书事件二级去重窗口（秒），默认 45
     export FEISHU_DEDUP_SECONDS=60
     # 可选：DeepSeek，如不设置则自动使用 Mock
     # export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
     # 可选：切换到本地 Ollama
     # export LLM_BACKEND=ollama
     # export OLLAMA_MODEL="qwen3-vl:8b"
     # export OLLAMA_BASE_URL="http://localhost:11434"
     # 本地超时与重试（可根据机器性能调整）
     # export OLLAMA_TIMEOUT=60          # HTTP 超时（秒）
     # export OLLAMA_RETRIES=1           # HTTP 重试次数
     # export OLLAMA_CLI_TIMEOUT=300     # CLI 兜底超时（秒）
     # 仅本地严格模式（失败不回退 Mock；用于生产或验收）
     # export OLLAMA_STRICT_LOCAL=true
     ```
  2) 启动 Flask 服务（默认端口 8080，避开 macOS AirPlay 占用的 5000）：
     ```bash
     # 使用 DeepSeek（默认）
     python3 feishu_server.py
     # 或使用本地 Ollama（推荐提前 ollama pull qwen3-vl:8b）
     python3 feishu_server.py --llm-backend ollama --ollama-model qwen3-vl:8b --ollama-base-url http://localhost:11434
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

- 企业微信开发联调（简化模式）
  - 额外设置环境变量：
    ```bash
    export WECOM_CORP_ID="wwxxxxxxxxxxxx"
    export WECOM_CORP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxx"
    export WECOM_AGENT_ID="1000002"
    # 开启安全模式（回调验签与加解密）需要：
    export WECOM_TOKEN="your_token_here"
    export WECOM_ENCODING_AES_KEY="your_43_chars_encodingaeskey"
    ```
  - 在企业微信“接收消息”配置公网地址指向：`https://<你的域名>.loca.lt/wecom/event`
  - 安全模式下，系统会使用 token 与 encodingaeskey 对 URL 验证（GET echostr）进行验签与解密；生产建议开启。
  - 发送“王先生的儿子考上了清华大学”等消息，机器人将先回“客户画像”文本，再回图片。

- 本地快速验证（不依赖飞书）：
  ```bash
  # DeepSeek（默认）
  python3 -c "from agents import main_agent; r = main_agent.run_and_return('王先生的儿子考上了清华大学'); import json; print(json.dumps(r, ensure_ascii=False, indent=2))"
  # 使用本地 Ollama
  python3 main.py --llm-backend ollama --ollama-model qwen3-vl:8b
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
      - 庆祝 Agent 的提示词明确“禁止生日/节日词汇”，避免误生成“生日快乐”等不相关内容；
      - 如果输出仍包含生日相关词，将自动二次约束重写，保证准确性；
    - 使用 Pillow 生成贺卡图片；
    - 返回结构化结果：`{ profile, blessing, image_path, text }`。
  - 飞书发送层：
    - 先发送“客户画像 JSON 卡片”；
    - 再上传图片并发送“图片卡片”。

- 幂等、并发与重试处理
  - 去重层次：
    1) `message_id` 去重（避免飞书重试带来重复事件）；
    2) `chat_id + 文本` 在时间窗口内的二级去重（避免不同 message_id 的相同内容重复处理，可调 `FEISHU_DEDUP_SECONDS`）；
    3) in-flight 并发去重（同一 `chat_id+文本` 同时只允许一个线程处理）；
  - LLM 调用容错（本地优先）：
    - Ollama：优先 `/api/chat`，遇 404/405 → `/api/generate`，HTTP 均失败 → CLI 兜底；
    - 可配置 `OLLAMA_TIMEOUT`、`OLLAMA_RETRIES`、`OLLAMA_CLI_TIMEOUT`；
    - `OLLAMA_STRICT_LOCAL=true` 时，所有本地路径失败将抛错，不回退 Mock；
  - 过滤非用户消息（避免机器人自发消息回环）。

## 4. 依赖组件

- Python 3.9+
  - Flask（Webhook 服务）
  - requests（HTTP 调用 Feishu/OpenAPI）
  - Pillow（贺卡图片生成）
  - Faker（私行客户画像模拟）
- Node.js（可选，用于内网穿透）
  - localtunnel（`npm i -g localtunnel`）
- 可选：DeepSeek（`DEEPSEEK_API_KEY`）或本地 Ollama（`OLLAMA_MODEL`、`OLLAMA_BASE_URL`）；未设置将使用 Mock。支持严格本地模式（`OLLAMA_STRICT_LOCAL=true`）。
- 企业微信接口：需要 `WECOM_CORP_ID`、`WECOM_CORP_SECRET`、`WECOM_AGENT_ID`
  - 安全模式（推荐）：`WECOM_TOKEN`、`WECOM_ENCODING_AES_KEY`（43 位）
  - 依赖：`pycryptodome`（AES-CBC 解密）
    ```bash
    pip install pycryptodome
    ```

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

若需企业微信联调，在后台将 `https://<你的域名>.loca.lt/wecom/event` 配置为接收地址（开发阶段直通 JSON，生产环境需启用加解密流程）。

---

### 目录结构（简要）

```
iceman/
├─ feishu_server.py       # 飞书 Webhook 服务（异步处理、幂等、卡片/图片发送）
├─ agents.py              # MainAgent + 子 Agent（生日/节日/喜事），结构化返回
├─ skills/                # 技能系统（内置 + 外部扩展）
│  ├─ __init__.py         # 导出 skills 单例（SkillManager）
│  ├─ manager.py          # 技能注册/调用，skills.md 注册表、外部技能安装、按需加载、HTTP 技能
│  ├─ builtin/            # 内置技能
│  │  ├─ profile.py       # 客户画像查询
│  │  └─ card.py          # 贺卡图片生成
│  └─ external/           # 外部下载的技能目录
├─ profile_service.py     # Faker 模拟私行客户画像（称呼 → 性别一致）
├─ llm_client.py          # LLM 客户端（DeepSeek / 本地 Ollama；未配置则 Mock）
├─ output_cards/          # 自动生成的贺卡图片输出目录
└─ README.md
```

## Skills 扩展与下载

- 调用统一入口：
  - 在代码中使用：`from skills import skills`
  - 内置能力：
    - `skills.query_profile(name)`
    - `skills.generate_card(content, theme)`
- skills.md 注册表（启动时解析，大模型可读）
  - 在项目根目录的 `skills.md` 中以 ```skill 包裹 JSON 描述技能（便于大模型识别与按需加载）：
    - 字段：`name`、`description`、`entry`（模块:类名）、`methods`、`parameters`（JSON Schema/子集）、`returns`、`auto_load`
    - 也支持 HTTP 技能：`type:http`、`endpoint`、`method`、`headers`（支持 `${ENV}` 展开）、`timeout`
  - 调用时若技能未加载且在注册表中，将即时安装/加载（无预编排）。
- 安装外部技能（兼容 manifest）：
  - manifest 示例（JSON）：
    ```json
    {
      "name": "example_skill",
      "module_url": "https://your.cdn.com/example_skill.py",
      "module_file": "skill.py"
    }
    ```
  - 运行时安装：
    ```python
    from skills import skills
    skills.install_from_manifest("https://your.cdn.com/example_skill_manifest.json")
    ```
  - 安装后会加载至 `skills/external/<name>/` 并自动导入。如果模块提供 `register(manager)` 方法，会在加载时调用；或者包含 `Skill` 类将作为 `<name>` 注册。

### 常见问题

- “没有响应”：确认 localtunnel 正在运行、飞书事件订阅地址指向 `/webhook/event` 且验证通过；确认应用已加入当前会话并发布了权限变更；群聊中请 @ 应用。
- “重复回复”：已加入三层防重（message_id / chat_id+文本窗口 / in-flight 并发）；如仍出现，请提供日志与时间戳。
- “DeepSeek 输出出现‘生日快乐’但场景并非生日”：庆祝 Agent 的提示词已明确禁用生日词汇，并有二次校正；如仍偶发可进一步收紧（例如模板化输出）。
- “本地模型超时”：增大 `OLLAMA_TIMEOUT`、`OLLAMA_CLI_TIMEOUT`；首次加载模型建议提高到 300–600 秒；严格本地模式可设 `OLLAMA_STRICT_LOCAL=true`。
