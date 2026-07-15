# Live 音色复刻与 Voice Lab 同步设计

## 目标

在现有 Voice Lab 中加入阿里云百炼 Qwen-Audio-Realtime 音色复刻入口。用户自行在阿里云 OSS 控制台上传参考音频，将可公开访问或带签名参数的 HTTPS URL 粘贴到 Web 页面；项目调用百炼复刻接口、保存返回的音色，并让该音色自动出现在 Live 角色音色选择中。

## 范围

- 支持 `qwen-audio-3.0-realtime-flash` 与 `qwen-audio-3.0-realtime-plus`。
- 两个模型的复刻音色严格隔离，不能跨模型使用。
- 同一参考声音若需同时支持 Flash 与 Plus，用户需要分别创建两次音色。
- 不接入 OSS SDK，不负责上传、删除或管理 OSS 对象。
- 不保存参考音频，也不持久化包含签名参数的音频 URL。
- 删除本地音色记录时暂不调用百炼远端删除接口。

## 用户流程

1. 用户在阿里云 OSS 控制台上传符合要求的 WAV、MP3 或 M4A 文件。
2. 用户在 Voice Lab 的音色管理抽屉切换到“Live 音色复刻”。
3. 用户填写易读音色名，选择 Flash 或 Plus，并粘贴 OSS HTTPS URL。
4. 前缀默认使用 `livevoice`，允许修改为最长 10 位的英文字母或数字。
5. 后端调用百炼 `voice-enrollment` / `create_voice` 接口。
6. 成功后将返回的 `voice_id` 保存到现有 `toolbox_tts_voices` 表。
7. Live 页面读取同一用户的音色目录，只展示与当前 Live 模型精确匹配的音色名；开始实时会话时仍发送真实 `voice_id`。

## 后端设计

### 请求契约

新增 `POST /toolbox/tts/voices/enroll-live`：

```json
{
  "user_id": "alice@example.com",
  "display_name": "电影旁白",
  "target_model": "qwen-audio-3.0-realtime-plus",
  "prefix": "livevoice",
  "audio_url": "https://example.oss-cn-beijing.aliyuncs.com/sample.mp3?..."
}
```

校验规则：

- `display_name`：去除首尾空格后 1–80 字符。
- `target_model`：只能是当前两个 Live 模型之一。
- `prefix`：1–10 位 ASCII 字母或数字。
- `audio_url`：必须是 HTTPS URL，最大 4096 字符；保留完整查询参数发送给百炼。

### 百炼调用

调用现有北京业务空间域名：

```text
https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/customization
```

请求体固定为：

```json
{
  "model": "voice-enrollment",
  "input": {
    "action": "create_voice",
    "target_model": "qwen-audio-3.0-realtime-plus",
    "prefix": "livevoice",
    "url": "https://..."
  }
}
```

成功后读取 `output.voice_id`。失败时向前端返回可读错误，但不回显带签名的完整音频 URL。

### 持久化

复用 `toolbox_tts_voices`：

- `provider = "bailian"`
- `display_name = 用户填写名称`
- `external_voice_id = 百炼返回 voice_id`
- `voice_kind = "cloned"`
- `bound_model = target_model`
- `provider_metadata = {"usage": "live", "prefix": "livevoice", "request_id": "..."}`

扩展现有模型绑定校验，使百炼音色既允许 CosyVoice 3.5 Plus/Flash，也允许 Qwen-Audio-Realtime Plus/Flash，但每条记录只能绑定一个精确模型。

## Live 同步设计

- Live 页面加载角色数据时，同时加载当前用户的 `toolbox_tts_voices`。
- 自定义音色选择器展示 `display_name`，选中值使用 `external_voice_id`。
- 只展示 `provider = bailian`、`usage = live` 且 `bound_model` 等于当前 Live 模型的记录。
- 保留原有“手动输入 Voice ID”入口，兼容已存在的角色和外部创建音色。
- 若用户切换 Flash/Plus 后，当前角色保存的目录音色与新模型不兼容：
  - 页面显示明确警告；
  - 禁止开始通话；
  - 角色原始音色配置不被静默覆盖。
- 后端在建立实时会话前再次校验目录音色绑定，防止绕过前端调用错误模型。

## Voice Lab 界面

音色管理抽屉增加两种模式：

- “登记已有音色”：保留现有音色名、音色 ID、供应商和绑定模型表单。
- “Live 音色复刻”：音色名、目标模型、英文前缀、OSS 音频 URL。

提交时按钮进入复刻状态；成功后关闭或清空复刻表单、刷新目录，并提示该音色已同步到 Live。页面不展示或保存完整签名 URL。

## 错误处理

- 百炼配置缺失：HTTP 503。
- 表单或模型绑定错误：HTTP 422。
- 百炼拒绝、无法下载音频或复刻失败：HTTP 502，并返回经过清理的错误摘要。
- 百炼成功但本地保存失败：返回失败，不伪装为已同步；日志记录 `request_id` 便于排查。
- Live 使用了已登记但模型不匹配的音色：阻止会话建立并提示重新选择。

## 测试

- Schema：URL、前缀和目标模型校验。
- 百炼适配器：请求头、请求体、`voice_id` 解析与错误脱敏。
- API：成功复刻后写入正确名称、ID、模型和 metadata；用户数据隔离。
- Live 后端：匹配模型允许启动，不匹配模型拒绝启动。
- 前端：复刻音色按模型过滤、显示名称但提交 ID、切换模型后的不兼容状态。
- 全量后端测试、前端单元测试、类型检查与生产构建。

