# Dapper Coding 定时问候 Agent

这是一个基于 Python 的自动化脚本：
- 每天早上 8:00 触发任务
- 根据用户画像调用 LLM 生成个性化问候
- 通过飞书 OpenAPI 给对应用户推送消息

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

支持两种方式：

1) 直接在当前终端设置 `$env:*`
2) 在项目根目录写 `.env`（脚本会按自身路径自动加载，不受当前工作目录影响）

Windows PowerShell 示例：

```powershell
$env:FEISHU_APP_ID="YOUR_FEISHU_APP_ID"
$env:FEISHU_APP_SECRET="<YOUR_FEISHU_APP_SECRET>"
$env:LLM_API_KEY="<YOUR_LLM_API_KEY>"
$env:LLM_BASE_URL="https://api.minimax.chat/v1"
$env:LLM_MODEL="minimax-m2.7"
$env:HEWEATHER_API_KEY="<YOUR_HEWEATHER_API_KEY>"
$env:WEATHER_LOCATION="101020100"
$env:WEATHER_LAT="31.2304"
$env:WEATHER_LON="121.4737"
$env:EXTERNAL_TIMEOUT="4"
$env:NEWS_ENABLED="true"
$env:WEATHER_ENABLED="true"

# 可选：受限网络场景下关闭主源，直接走回退源
$env:V2EX_ENABLED="false"
$env:QWEATHER_ENABLED="false"

# 可选：requests 代理（与 VPN 并行时常用）
$env:REQUESTS_PROXY_ENABLED="true"
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# 可选：如果暂时不想接天气 API，也可以直接用文本兜底
$env:WEATHER_INFO="上海小雨，气温 12-16℃"

# 可选：如果暂时不想依赖新闻 API，也可以用文本兜底
$env:DAILY_NEWS="AI 视觉与自动化办公方向有新进展"

# 可选：本地调试时使用模拟 LLM（不请求真实模型）
$env:LLM_SIMULATE="true"

# 可选：本地调试时模拟飞书发送（不请求真实飞书）
$env:FEISHU_SIMULATE="true"

# 可选：立即执行一次（默认是 schedule）
$env:RUN_MODE="once"

# 可选：覆盖默认用户画像（JSON 字符串）
$env:USER_PROFILES_JSON='[{"open_id":"ou_xxx","feature":"喜欢晨跑和咖啡"}]'
```

> 说明：未开启模拟模式时，缺失关键环境变量会在启动时报错。
> 如需指定非默认 `.env` 路径，可设置 `DAPPER_ENV_FILE=E:\path\to\.env`。

## 3. 运行

```bash
python dapper_coding_agent.py
```

- `RUN_MODE=once`：立即执行一次
- `RUN_MODE=schedule`：启动 APScheduler，固定每天 08:00 执行
- `RUN_MODE=healthcheck`：执行配置/外部依赖/LLM/飞书预检并返回退出码
- `RUN_MODE=server`：启动 FastAPI Webhook 服务（0.0.0.0:8000）

健康检查示例（不真实发飞书）：

```powershell
$env:RUN_MODE="healthcheck"
$env:FEISHU_SIMULATE="true"
& "D:\Anaconda3\envs\Dapper_Coding\python.exe" dapper_coding_agent.py
```

## 4. 说明

- 飞书接口使用：
  - 鉴权：`/open-apis/auth/v3/tenant_access_token/internal`
  - 发送消息：`/open-apis/im/v1/messages?receive_id_type=open_id`
- LLM 使用 OpenAI 兼容的 `chat/completions` 格式。
- 问候语会结合 `current_time`、实时天气、V2EX 新闻和用户画像拼接提示词。
- 新闻源优先 `V2EX`，失败自动回退 `Hacker News`；天气源优先 `QWeather`，失败自动回退 `Open-Meteo`，再回退到 `WEATHER_INFO` 文本兜底。
- 如果密钥曾出现在聊天记录、代码仓库或日志中，请尽快在对应平台完成密钥轮换。

## 5. Learning Scout v1

- 新增 `feeds.yaml` 作为 RSS/Atom 订阅配置；`enabled: false` 的源会自动跳过。
- 新增 `learning_scout.py`，负责抓取、正文提取、LLM 摘要打标、入库、飞书卡片推送。
- 新表 `learning_scout_items` 创建在 `dapper_memory.db`，通过 `content_hash` 去重。
- 调度模式下会在每天 `08:05` 执行 Learning Scout（早安任务后 5 分钟）。

可选环境变量：

```dotenv
SCOUT_ENABLED=true
SCOUT_DAILY_LIMIT=5
```

单独运行 Learning Scout：

```powershell
& "D:\Anaconda3\envs\Dapper_Coding\python.exe" .\learning_scout.py
```

## 6. Learning Scout v3

- 新增 `learning_feedback`、`learning_resources` 表，以及 `click_count` / `series_id` 字段。
- 新增 `/learning/search`、`/learning/feedback`、`/learning/series`、`/learning/feed-recommendations` 接口。
- `RESOURCE_DOWNLOAD_ENABLED=false` 时默认不下载 PDF/视频资源；开启后才会尝试提取。

## 7. Web 管理界面

- 后端已支持静态托管：`/admin`
- 访问 `/admin` 需 HTTP Basic Auth（用户名固定 `admin`）
- 密码来自环境变量 `WEB_ADMIN_PASSWORD`

新增环境变量：

```dotenv
WEB_ENABLED=true
WEB_ADMIN_PASSWORD=YOUR_WEB_ADMIN_PASSWORD
```

如需本地快速验证：

```powershell
$env:RUN_MODE="server"
$env:WEB_ENABLED="true"
$env:WEB_ADMIN_PASSWORD="YOUR_WEB_ADMIN_PASSWORD"
& "D:\Anaconda3\envs\Dapper_Coding\python.exe" .\dapper_coding_agent.py
```

