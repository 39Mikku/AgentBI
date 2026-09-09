# AgentBI 前端

Vue 3、TypeScript、Vite 与 Pinia 构成的本地工作台。完整启动和能力配置见 [根 README](../README.md)。

- `src/views/`：Studio、Live、Playground、Test 和工具箱页面。
- `src/stores/workspace.ts`：从后端初始化本地身份，页面就绪后挂载业务工作台。
- `src/api/`：REST 与流式接口。
- `src/router/`：工作台路由，旧 `/login` 与 `/about` 跳转到首页。

开发服务器将 `/api` 转发到 FastAPI，并代理 WebSocket。默认后端为 `127.0.0.1:8000`，可通过 `AGENTBI_BACKEND_URL` 调整。`npm run build` 执行类型检查及构建；当前标准运行入口为 Vite 开发服务器。
