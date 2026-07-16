# Seedance 视频提供商接入设计

## 目标

在保留单一 `generate_video` 原子工具和现有异步视频卡片交互的前提下，把 Agnes Video v2.0 与火山方舟 Doubao Seedance 1.0 Pro 作为可配置的视频生成模型。Seedance 同时支持文生视频和使用当前用户消息首张图片的图生视频。

## 架构

- `VideoGenerationService` 继续负责本地任务、后台轮询、视频下载、附件归档和消息绑定。
- 提供商差异下沉到适配器：Agnes 与 Ark Seedance 分别实现创建、查询、下载和状态归一化。
- 服务通过配置中的 `provider` 和 `model` 选择适配器；任务记录持久化提供商和模型，使服务重启后可恢复正确的轮询链路。
- 主模型始终只看到一个 `generate_video` 工具，不直接管理 API Key 或提供商协议。

## 配置

视频能力配置新增：

- `provider_model`: `agnes-video-v2.0` 或 `doubao-seedance-1-0-pro-250528`
- `default_aspect_ratio`
- `default_duration_seconds`
- `resolution`: Seedance 使用 `480p` 或 `720p`
- `generate_audio`: 保留在内部任务快照中，但 Seedance 1.0 Pro 固定为关闭
- `watermark`: 是否添加平台水印

前端根据模型展示合法选项。Agnes 保留 3/5/10/18 秒；Seedance 1.0 Pro 使用 5/10 秒与 480p/720p。Seedance 支持 `adaptive` 和 `21:9`，不开放同步音频。

## 图生视频

`generate_video` 增加可选的 `use_attached_image`。为 true 时，执行层读取当前用户消息绑定的第一张图片并转为 Data URL，作为 Ark `image_url` 内容传入；没有附件时返回明确错误。Agnes 不支持该参数。

## 状态与进度

- Ark `queued` -> `queued`
- Ark `running` -> `in_progress`
- Ark `succeeded` -> `completed`
- Ark `failed`、`expired`、`cancelled` -> `failed`

Ark 不提供百分比进度，数据库允许 `progress` 继续保留阶段值，前端对 Ark 展示不定进度，不伪造百分比。成功后立即下载 `content.video_url`，避免 24 小时 URL 过期。

## 环境变量

- `ARK_API_KEY`
- `ARK_VIDEO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`

火山视频 Key 与现有火山 TTS 的 App ID/Access Token 独立。

## 验证

- 适配器请求与响应契约单元测试。
- 模型相关配置与数据库迁移测试。
- 服务按任务提供商恢复轮询、图生视频附件读取和归档测试。
- 前端配置选项与视频卡片模型标签测试。
- 后端完整测试、前端完整测试和生产构建。
