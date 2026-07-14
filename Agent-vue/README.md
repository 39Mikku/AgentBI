# AgentBI · 智能体控制台前端

基于 Vue 3 + Vite + TypeScript 构建的智能体控制台 Web UI，对接 AgentBI FastAPI 后端的邮箱验证码登录体系。

## 功能特性

- **分屏登录页**：左侧深色品牌视觉区（动态算力网格 + 数据流光晕），右侧步骤式表单
- **邮箱验证码全链路**：输入邮箱 → 发送验证码（60s 倒计时）→ 输入验证码 → 登录，完整对接后端 `/send_code` 与 `/login` 接口
- **登录守卫**：未认证用户自动重定向至登录页，已登录用户跳转控制台
- **智能体控制台**：登录后展示能力矩阵卡片（邮件投递、数据查询、记忆系统、契约校验）
- **深色 / 浅色双主题**：跟随系统偏好，支持手动切换并持久化
- **响应式布局**：移动端自动收起品牌视觉区，表单自适应
- **错误处理**：网络异常、服务不可达、验证码错误等场景均有清晰提示

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | Vue 3.5 (`<script setup>`) |
| 构建 | Vite 8 |
| 语言 | TypeScript 6 (严格模式) |
| 状态 | Pinia 3 |
| 路由 | Vue Router 5 |
| 设计 | Apple-inspired 设计 tokens（System Blue / DM Sans + Sora / 胶囊组件） |

## 项目结构

```text
src/
├── api/
│   ├── index.ts          # API 服务层（fetch 封装 + sendCode/login）
│   └── types.ts          # 接口类型定义
├── assets/
│   └── main.css          # 全局样式 + 设计 tokens（浅/深主题）
├── components/
│   └── ThemeToggle.vue   # 主题切换组件
├── router/
│   └── index.ts          # 路由配置 + 登录守卫
├── stores/
│   ├── auth.ts           # 认证状态管理（登录流程、倒计时、持久化）
│   └── counter.ts        # 示例 store（脚手架遗留）
├── views/
│   ├── HomeView.vue      # 登录页（分屏 + 验证码表单）
│   └── AboutView.vue     # 控制台（登录后能力矩阵）
├── App.vue               # 根组件 + 路由过渡
└── main.ts               # 应用入口
```

## 快速开始

### 一键启动

双击 `start.bat`，脚本会自动检查依赖并启动开发服务器，随后自动打开浏览器。

### 手动启动

```sh
npm install
npm run dev
```

启动后访问 http://localhost:5173

### 后端对接

前端通过 Vite dev server 代理 `/api` 请求到 FastAPI 后端（`http://127.0.0.1:8000`），自动剥离 `/api` 前缀，规避开发期 CORS。

启动后端：

```sh
cd ../AgentBI
python main.py
```

需确保 Redis（127.0.0.1:6379）已运行，且 `.env` 中配置了邮箱授权码与大模型 API Key。

## 接口契约

| 接口 | 方法 | 入参 | 返回 |
|------|------|------|------|
| `/api/send_code` | POST | `{ email: string }` | `{ code: 200, msg: string }` |
| `/api/login` | POST | `{ email: string, code: string }` | `{ code: 200, msg: string }` |

业务约定 `code === 200` 为成功。

## 设计说明

视觉基底取自 Apple-inspired 设计库：System Blue（`#007AFF`）主色、DM Sans 正文 + Sora 展示字体 + JetBrains Mono 等宽、1.2rem 圆角、胶囊按钮、focus ring 输入框。登录页左侧视觉区以动态网格与呼吸光晕隐喻智能体的算力与数据流。

## 可用脚本

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器（热更新） |
| `npm run build` | 类型检查 + 生产构建 |
| `npm run type-check` | TypeScript 类型检查 |
| `npm run lint` | ESLint + OxLint 代码检查 |
| `npm run format` | 代码格式化 |
