# AgentBI 开发说明

## 目录与运行路径

```text
Agent-vue/src/           Vue 页面、组件、状态及 API 客户端
Agent-vue/tests/         迁入统一 Vitest 入口的回归用例
AgentBI/main.py          FastAPI 生命周期和路由注册
AgentBI/src/api/         REST / SSE / WebSocket 入口
AgentBI/src/services/    模型、媒体、工具箱及业务服务
AgentBI/src/agents/      对话编排和专项子代理
AgentBI/src/repositories/ SQLite 数据读写
AgentBI/tests/           unittest 回归用例
AgentBI/vendor/          内置音乐服务包装及独立 Node 依赖
scripts/                Windows 初始化、启动与空库检查
```

浏览器先调用 `/api/workspace`，拿到稳定资料后再挂载业务页面；旧接口继续使用同一个 user_id，兼容已有数据库。Live WebSocket 也使用该工作区 ID。模型供应商保持工作区全局配置。

新增 `local_workspace` 表保存既有资料选择。原用户表、历史 ID 及旧库中的验证码表保持原样；新版停止创建及使用验证码表。资料显示名与头像继续通过 `/user-profile` 更新。

## 本地验证

```powershell
# 仓库根目录，使用启动器生成的环境
.envScriptspython.exe -m unittest discover -s AgentBI/tests -q
.envScriptspython.exe scripts/check-startup.py
npm --prefix Agent-vue run build
npm --prefix Agent-vue run test:unit
```

如果使用 `.venv`，将命令中的 `venv` 替换为 `.venv`。空库检查临时指定数据库路径并关闭音乐服务。自动工作流在 Windows/Python 3.13/Node 22.23.1 执行相同检查。

身份变更需覆盖：空库首次进入、单份旧资料沿用、多份旧资料选择及重启持久化。页面变更至少在浏览器实际走一次操作。真实模型、实时语音与外部服务按已有配置手动验收。

## 依赖与启动器

后端 `requirements.txt` 描述版本范围，`requirements-lock.txt` 记录本轮验证版本；启动器同时安装二者。更新依赖时，在独立环境从 requirements.txt 重新解析，完成相关回归后更新锁定文件：

```powershell
python -m venv .venv-update
..venv-updateScriptspython.exe -m pip install -r AgentBI/requirements.txt
..venv-updateScriptspython.exe -m unittest discover -s AgentBI/tests -q
..venv-updateScriptspython.exe -m pip freeze > AgentBI/requirements-lock.txt
```

Vue 和音乐 wrapper 各自保留 package-lock，启动器使用 npm ci。清单哈希保存在对应环境目录下；清单变化、安装不完整或依赖检查失败时重新同步。

需要 Vue DevTools 时，在启动前设置 `AGENTBI_DEVTOOLS=true`。默认工作台隐藏开发调试浮层。

`start-agentbi.cmd` 默认打开日志窗口。自动检查可使用 `-NoBrowser -Hidden`，日志输出到 `AgentBI/logs/`；隐藏模式按输出的进程 ID 管理本次服务。`-SetupOnly` 只安装依赖；端口参数同时配置前端代理。

服务根接口和前端 `/__agentbi` 返回源码目录标识，启动器据此区分不同克隆。默认 URL 为前端 5173、后端 8000、音乐 3300。

## 本轮整理

- 本地工作区取代邮箱验证码入口；默认进入工作台。
- 应用介绍转向独立官网，共享品牌和模块目录继续保留。
- 补齐 vendor 依赖安装和已有环境同步。
- Playground 删除请求按 HTTP 状态反馈成功或失败。
- 手动配置的默认模型直接进入可选列表；补齐 Windows 时区数据库依赖 tzdata。
- 原有两组前端测试统一收集，新增身份及删除失败回归。
- 增加 MIT 许可、运行文档与基础自动检查。

统一数据根目录、应用打包和更多平台支持可按后续实际需求推进。
