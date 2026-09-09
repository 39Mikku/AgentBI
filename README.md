<div align="center">

<img src="Agent-vue/public/brand/agentbi-mark.svg" width="88" alt="AgentBI Logo" />

# AgentBI

**把对话、实时语音、角色叙事和日常工具放进同一个本地 AI 工作台。**

![License](https://img.shields.io/badge/license-MIT-D9FF36?style=flat-square&labelColor=171717)
![Local](https://img.shields.io/badge/workspace-local_first-EEECE6?style=flat-square&labelColor=171717)
![Stack](https://img.shields.io/badge/Vue_3_×_FastAPI_×_SQLite-80F4DB?style=flat-square&labelColor=171717)

[项目官网](https://agentbi.39miku.tech/) · [快速开始](#快速开始) · [能力配置](#能力配置) · [本地资料与数据](#本地资料与数据)

</div>

![AgentBI](Agent-vue/public/brand/og-agentbi.png)

AgentBI 起于学校就业实训，后来逐渐变成日常使用的个人工作台，现在以 MIT 协议开源。打开本地页面即可使用，首次运行自动创建工作区。模型服务和第三方能力按需配置，聊天、资料与附件存储在本地。

## 可以做什么

| 空间 | 当前能力 |
| --- | --- |
| **Studio** | OpenAI 兼容供应商、流式对话、消息编辑与分支、助手、长期记忆、历史向量检索、多模态附件、工具及子代理 |
| **Live** | 实时语音、字幕、用户打断、角色与音色、通话历史和角色记忆 |
| **Playground** | 角色与世界、世界书、模块化提示、叙事状态、长会话精炼及语音播放 |
| **Test** | 知识测试、趣味测试、结构化出题、自动分析、结果归档与重测 |
| **Toolbox** | TTS 对比、表情包制作、萌娘百科归档、文件时间管理及自动输入 |

消息分支基于 DAG 保存。上下文可使用滚动窗口或后台压缩；完整原始消息继续保留。工具、正文与子代理过程按实际时间线展示。

## 快速开始

### Windows 一键启动

准备 **Python 3.11+（推荐 3.13）** 与 **Node.js 22.18+ 的 22.x 或 24.12+**，然后执行：

```powershell
git clone https://github.com/39Mikku/AgentBI.git
Set-Location AgentBI
.\start-agentbi.cmd
```

脚本会创建 Python 虚拟环境、复制 `.env.example`、安装后端与前端锁定依赖，并在启用音乐时安装内置音乐服务依赖。服务就绪后打开 **http://localhost:5173/**。关闭 Backend / Frontend 日志窗口即可结束对应服务。

重复运行时会检查依赖清单与安装状态，只复用同一份源码目录的服务。端口已占用时可指定另一组：

```powershell
.\start-agentbi.cmd -BackendPort 18080 -FrontendPort 15173
# 仅准备依赖
.\start-agentbi.cmd -SetupOnly
```

### 第一次对话

1. 打开首页，进入 **Studio** 或 **模型工作室**。
2. 添加 OpenAI 兼容供应商，填写 API 地址和 Key，刷新或填写模型列表。
3. 在 Studio 选择供应商和模型，发送第一条消息。
4. 在助手管理中设置提示词、记忆和所需能力。

主工作台可以在空配置下打开；模型调用在配置供应商后启用。邮件账户仅用于邮件能力。

### 手动启动

在仓库根目录初始化后端：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r AgentBI/requirements-lock.txt -r AgentBI/requirements.txt
# 首次运行复制一次
Copy-Item AgentBI/.env.example AgentBI/.env
```

准备前端与默认启用的音乐服务：

```powershell
npm --prefix Agent-vue ci
npm --prefix AgentBI/vendor/netease-music-api ci
```

在两个终端中分别运行：

```powershell
# 终端 1：仓库根目录
.\venv\Scripts\python.exe -m uvicorn AgentBI.main:app --host 127.0.0.1 --port 8000
```

```powershell
# 终端 2：仓库根目录
npm --prefix Agent-vue run dev
```

Windows 为主要运行平台。macOS/Linux 可用 `python3 -m venv venv`，将上述 Python 路径替换为 `./venv/bin/python`，用 `cp` 复制示例配置；自动输入功能仅支持 Windows 桌面。

## 能力配置

环境配置示例在 [AgentBI/.env.example](AgentBI/.env.example)。编辑后重启后端。

| 能力 | 配置位置与前提 |
| --- | --- |
| 普通对话、测试、Playground | 模型工作室中配置兼容供应商；各工作台选择模型 |
| 总结、记忆、向量检索 | 应用内模型路由配置；向量检索需可用的 embedding 模型 |
| Live | `DASHSCOPE_API_KEY`，按服务需要填写 `DASHSCOPE_WORKSPACE_ID` |
| TTS | 按所选适配器填写 MiniMax、百炼、MiMo 或火山引擎配置 |
| 网易云音乐 | 内置服务依赖、`NCM_ENABLED`；个性化内容按需配置 `NCM_COOKIE` |
| Bilibili | 安装 `bili` CLI，例如 `uv tool install bilibili-cli`，可通过 `BILI_CLI_COMMAND` 指定命令 |
| 搜索 | `TAVILY_API_KEY` |
| 邮件 | `EMAIL_HOST`、`EMAIL_FROM`、`EMAIL_PASSWORD`、`EMAIL_PORT`（默认 465） |
| 图片 | 能力配置中的 Lite 模式配置或 Pro 模式的 Codex OAuth 连接 |
| 视频 | Agnes 使用 `AGNES_API_KEY`，火山方舟使用 `ARK_API_KEY` |
| 本地文件与自动输入 | 本机目录和桌面；自动输入仅支持 Windows |

将 `NCM_ENABLED=false` 可跳过音乐依赖初始化与后台音乐服务。其余第三方服务按需配置。

## 本地资料与数据

空数据库自动建立本地资料。旧数据库只有一份资料时直接沿用；存在多份时首次打开选择一次，选择结果保存在 SQLite 中。旧 user_id、聊天、助手和记忆保持原有归属。

| 路径 | 内容 |
| --- | --- |
| `AgentBI/data/agentbi.sqlite3` | 资料、工作区选择、会话、消息、配置、记忆和测试等 |
| `AgentBI/data/chat-attachments/` | 上传附件 |
| `AgentBI/data/generated-images/` | 生成图片及视频资产 |
| `AgentBI/data/codex-image-oauth.json` | 图片能力连接状态 |
| `AgentBI/.env` | 环境配置 |
| `AgentBI/logs/` | 运行日志 |

备份时先关闭后端，再复制完整 `AgentBI/data/` 和 `.env`。`CHAT_SQLITE_PATH` 只改变数据库位置，附件与生成内容仍位于上述目录；设置自定义数据库路径时一并保存这些文件。

## 常见问题

- **依赖安装中断**：重新运行根目录启动脚本，它会重新检查环境和依赖标记。
- **端口被占用**：通过 `-BackendPort`、`-FrontendPort` 改用另一组端口。
- **进入页面但模型无法调用**：在模型工作室确认供应商、API 地址与模型选择。
- **音乐不可用**：确认 vendor 依赖安装完成，检查 `/api/music/status` 与后端日志。
- **历史资料选择错误**：可在浏览器调用 `PUT /api/workspace`，提交 `{"user_id":"原资料ID"}` 后刷新。可选 ID 由 `GET /api/workspace` 的 `profiles` 返回。

## 许可

项目保持本地个人工具定位，欢迎可复现的问题反馈与小范围改进。

本仓库原创代码采用 [MIT License](LICENSE)，Copyright © 2026 39Mikku。第三方依赖保留各自许可。
