# Gemini 推理摘要与强度控制设计

## 目标

让 Studio 在使用 Gemini 2.5/3.x 文本模型时显式请求 thought summaries，按现有 SSE 时间线实时展示，并在聊天输入框附近提供持久化的低/中/高推理强度选择。

## 已验证的上游行为

- 当前 OpenAI 兼容网关接受 `extra_body.google.thinking_config` 形式的 Gemini 扩展参数。
- 同时传入 `thinking_level` 与 `include_thoughts: true` 后，网关以 `delta.reasoning_content` 流式返回摘要。
- `low` 与 `high` 均已通过真实请求验证；单独传通用 `reasoning_effort` 加 `include_thoughts` 不会经当前网关返回摘要。
- 返回摘要使用 Markdown，并可能用独占一行的粗体文本表达阶段标题。

## 后端设计

新增一个聚焦 Gemini thinking 的纯函数模块，负责：

1. 判断模型是否为支持 thinking 的 Gemini 2.5/3.x。
2. 校验并规范化 `low | medium | high`，默认 `medium`。
3. 为 Gemini 请求生成：

```json
{
  "extra_body": {
    "google": {
      "thinking_config": {
        "thinking_level": "medium",
        "include_thoughts": true
      }
    }
  }
}
```

该扩展合并到 OpenAI SDK 的 `extra_body` 参数中。非 Gemini 模型不附加任何 Gemini 参数。

`thinking_level` 存入 `chat_preferences`，随发送、重试和编辑请求进入后端，并写入每次助手消息的 `model_snapshot`。它不进入对话正文，也不增加模型上下文。

`ChatAgent` 继续把 `delta.reasoning_content` 映射为现有 `reasoning_summary` 事件，所以 SSE、数据库字段和时间线结构保持兼容。

## 前端设计

- 当当前模型匹配 Gemini 2.5/3.x 时，在 composer 操作栏显示“推理 · 低/中/高”紧凑选择器。
- 当前值保存在既有聊天偏好中，刷新页面后恢复。
- 非 Gemini 模型隐藏控件，但保留已保存值，切回 Gemini 时继续使用。
- 推理摘要内容改用现有安全 Markdown 渲染器。
- 独占一行的 `**阶段标题**` 在渲染前转换为 `### 阶段标题`；原生 Markdown 标题保持不变。
- 流式分片仍先由 store 合并相邻 `reasoning_summary`，因此跨分片标题会在闭合后自动形成结构化标题。

## 错误与兼容策略

- 不静默降级或二次请求，避免同一用户消息产生不可见的重复计费。
- 上游拒绝 Gemini 参数时沿用现有流式错误展示。
- 只匹配 Gemini 2.5/3.x，避免给旧版 Gemini 或名称中偶然包含 gemini 的非聊天模型发送不支持参数。

## 验证

- Python 单元测试覆盖模型识别、参数构建、偏好持久化、请求透传和快照。
- Vitest 覆盖模型识别、标题规范化、偏好 API 映射和控件可见性所依赖的纯函数。
- 运行完整后端测试、前端单测、类型检查/生产构建。

