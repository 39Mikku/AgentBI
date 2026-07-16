# 原子生图能力设计说明

## 目标

在 Studio 主会话中加入一个由主模型直接调用的原子生图 Tool，并为项目内已有图片上传入口提供“上传图片 / 描述生图”双入口。生图支持 Lite 与 Pro 两种后端，统一使用用户级能力配置，生成物保存在本地并可随历史会话重新展示。

## 产品边界

- 一次调用只生成一张图片。
- 第一期只支持文生图，不支持参考图、局部编辑、批量生成。
- 主会话调用时，由主模型把用户意图规划成完整提示词并选择方形、横向或竖向画幅。
- 头像等上传窗口调用时，直接使用用户输入，不额外调用文本模型改写提示词。
- 图片卡片只提供预览、查看原图与下载；不提供“再次生成”按钮。
- 生图能力是原子 Tool，不建立子代理。

## 统一能力与适配器

注册能力 `tool.image_generation`，向主模型暴露 `generate_image(prompt, aspect_ratio)`。模式、模型和画质不作为 Tool 参数，避免主模型自行改变费用档位。

后端由 `ImageGenerationService` 统一调度：

- `LiteChatImageAdapter`：复用当前 Studio 提供商的 Base URL 与 API Key，使用能力配置中的独立 Gemini Image 模型，通过 OpenAI 兼容 `/chat/completions` 调用。解析常见 NewAPI 图片返回形态，包括 `message.images`、多模态 `content`、Data URL 与 Markdown 图片数据。
- `CodexImageAdapter`：使用 AgentBI 自己维护的 Codex OAuth 会话调用 Codex Responses 后端，宿主模型固定按兼容协议请求，图片工具模型为 `gpt-image-2`。

能力配置字段：

- `mode`: `lite` 或 `pro`，默认 `lite`。
- `lite_model`: Lite 生图模型名称。
- `pro_quality`: `low`、`medium` 或 `high`，默认 `high`。

Lite 在主会话中使用本轮聊天的提供商；在头像生成等独立入口中使用 Studio 当前持久化的提供商选择。Pro 不依赖 Studio 提供商。

## OAuth 与本地凭据

Codex OAuth 使用与 Codex CLI/IDE 完全独立的本地凭据文件，默认路径为 `AgentBI/data/codex-image-oauth.json`。该文件只包含此项目的 access token、refresh token、过期时间和账户 ID，不读取、不覆盖用户现有 Codex 登录文件。

能力配置页为 Pro 模式提供“连接 Codex / 断开连接”和连接状态。连接流程使用 OpenAI 设备码登录：页面打开官方设备登录地址并显示一次性设备码，后端独立轮询完成 token 交换与 refresh。它不占用本地回调端口。`AgentBI/data/` 已整体忽略，同时在根 `.gitignore` 增加凭据文件的显式规则，防止将来数据目录规则调整时误提交。

同一 ChatGPT 账户的服务用量仍然共享。Codex 私有兼容端点若发生变化，前端明确显示 Pro 调用失败，不自动切到 Lite。

## 图片持久化与卡片

生成结果写入：

```text
AgentBI/data/generated-images/<user-hash>/<conversation-or-direct>/<image-id>.png
```

聊天 Tool 结果以 `image.generated` 卡片事件写入消息时间线，卡片只保存可访问的媒体 URL、图片 ID、模式、模型、画幅、尺寸和提示词摘要，不保存 Base64。主模型获得的 Tool 结果也是紧凑 JSON，不把图片二进制放进上下文。

独立图片生成 API 返回同样的媒体描述。上传组件将图片读取为 Data URL 后再写入现有头像字段，因此不改变助手、Live 角色和用户头像当前的数据结构。

## 可复用图片选择器

新增 Vue 组件 `ImageSourcePicker`，具有两个页签：

- 上传：保留现有文件类型、大小校验与本地预览。
- AI 生成：输入图片描述、选择画幅并提交；直接调用图片 API，不调用聊天模型。

第一期接入所有现有图片上传入口：

- Studio 助手头像。
- Live 角色头像。
- Studio 左下角用户资料头像。

组件沿用各页面原有视觉语言，通过 CSS 变量适配浅色助手管理页、深色 Live 页和 Studio 资料弹层，不强行统一三个页面的主题。

## 后台生成状态

Pinia Chat Store 用 `Set<conversationId>` 或等价映射替代单一会话视角的生成状态：

- 流开始时记录发起会话 ID。
- 切换会话不终止流，也不丢失该会话的生成状态。
- 流结束、失败或手动停止时清除对应 ID。
- 当前会话输入区仍根据当前会话是否生成中决定展示“停止”按钮。
- 左侧会话项在生成中显示动态信号与“生成中”，完成后恢复日期。

本期保持一次只运行一个 Studio 生成请求的现有约束，不同时并发多条主会话生成；状态结构按会话维护是为了正确展示后台任务，而不是扩大并发行为。

## 错误处理

- Lite 缺少提供商或模型时给出明确配置提示。
- Pro 未连接或 token 刷新失败时提示重新连接。
- 上游返回非图片内容时报告“未返回可解析图片”，不保存空文件。
- Base64、MIME、文件大小和 PNG/JPEG/WebP 解码进行校验。
- OAuth、上游响应和日志不得输出 token、API Key 或完整 Base64。
- 失败的 Tool 结果进入时间线，主模型可以据此向用户说明，但不会伪造图片卡片。

## 验收标准

1. 默认助手自动挂载生图 Tool，自定义助手可单独勾选。
2. Lite 使用当前提供商的 `/chat/completions` 和配置的生图模型生成一张图片。
3. Pro 可独立连接 Codex、刷新凭据并使用 `gpt-image-2` 生成一张图片。
4. 图片卡片按调用时间线显示，刷新历史会话后仍可预览和下载。
5. 助手、Live 角色和用户头像均可上传或直接输入描述生图。
6. 头像描述不会经过主聊天模型改写。
7. 切换到其他会话后，原会话侧栏仍显示生成中；完成后自动清除。
8. OAuth 文件和生成图片不会进入 Git。
