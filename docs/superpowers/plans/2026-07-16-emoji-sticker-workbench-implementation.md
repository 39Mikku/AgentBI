# Emoji 贴纸工坊 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `工具箱/EmojiCut` 的贴纸表生成、智能切图、中文命名、成品预览和 ZIP 下载移植为 AgentBI 工具箱组件，并让 Lite/Pro 共用生图能力支持可选参考图。

**Architecture:** 生图与图片持久化继续由现有 `ImageGenerationService` 负责，参考图作为可选 Data URL 传入 Lite Chat Completions 或 Pro Responses `input_image`。贴纸切割、透明背景、描边和 ZIP 打包留在浏览器本地；后端只负责生成整张贴纸表以及调用当前 `vision` 模型做中文命名。整张贴纸表作为无聊天消息归属的正式工具箱资产进入附件库。

**Tech Stack:** FastAPI、Pydantic、SQLite、OpenAI-compatible Chat Completions、Codex Responses image tool、Vue 3、TypeScript、Canvas、JSZip、Vitest、unittest。

## Global Constraints

- AI 命名默认开启，输出简短中文名称。
- 先真实测试一次整批识别；效果不可靠时，前端固定改为逐张命名并限制并发。
- 贴纸文字默认开启，可关闭；关闭时生成提示词明确禁止文字、字幕和气泡文案。
- 高级切图参数默认折叠，默认值可直接产出可用结果。
- 只持久化整张生成贴纸表，单张切片和 ZIP 留在浏览器本地。
- 复用现有 Lite/Pro、提供商、OAuth 和 Image2 配置，不新增重复配置。
- 不修改 `工具箱/EmojiCut` 嵌套原项目；仅参考其行为。
- 不执行 git stage、commit、push，由用户手动提交。

---

### Task 1: Shared reference-image generation

**Files:**
- Modify: `AgentBI/src/schemas/image_generation_schema.py`
- Modify: `AgentBI/src/services/image_generation/lite_adapter.py`
- Modify: `AgentBI/src/services/image_generation/codex_adapter.py`
- Modify: `AgentBI/src/services/image_generation/service.py`
- Modify: `AgentBI/src/api/image_generation.py`
- Modify: `AgentBI/tests/test_image_generation_lite.py`
- Modify: `AgentBI/tests/test_image_generation_codex.py`
- Modify: `AgentBI/tests/test_image_generation_api.py`
- Modify: `AgentBI/tests/test_image_generation_service.py`
- Modify: `Agent-vue/src/api/image-generation-types.ts`
- Modify: `Agent-vue/src/api/image-generation.test.ts`

**Interfaces:**
- Consumes: `reference_image_data_url?: string` containing PNG/JPEG/WebP Base64 data.
- Produces: `ImageGenerationService.generate(..., reference_image_data_url=None)` and adapter calls preserving old text-only payloads.

- [ ] Write tests proving Lite uses `image_url + text`, Pro uses `input_image + input_text`, API forwards the reference, and text-only payloads remain unchanged.
- [ ] Run targeted backend/frontend tests and confirm the new assertions fail because reference-image arguments are absent.
- [ ] Add strict Data URL validation and pass the optional reference through schema, API, service and both adapters.
- [ ] Run targeted tests and confirm they pass.

### Task 2: Toolbox assets in attachment library

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/src/services/studio_asset_service.py`
- Modify: `AgentBI/src/services/image_generation/service.py`
- Modify: `AgentBI/tests/test_studio_asset_api.py`
- Modify: `Agent-vue/src/views/AttachmentsView.vue`

**Interfaces:**
- Consumes: generated image `scope_id`.
- Produces: unbound generated assets returned by `list_assets`, with nullable conversation fields and `metadata.scope_id`.

- [ ] Add a failing test that registers a generated image without binding it to a message and expects it in `/assets`.
- [ ] Replace asset-list inner joins with left joins while keeping search and conversation metadata stable.
- [ ] Merge `scope_id` into generated asset metadata and render `toolbox-emoji` as “贴纸工坊” in the attachment library.
- [ ] Run asset repository/API tests.

### Task 3: Chinese sticker naming service

**Files:**
- Create: `AgentBI/src/schemas/toolbox_emoji_schema.py`
- Create: `AgentBI/src/services/toolbox/emoji_naming.py`
- Create: `AgentBI/src/api/toolbox_emoji.py`
- Modify: `AgentBI/src/services/model_task_service.py`
- Modify: `AgentBI/main.py`
- Create: `AgentBI/tests/test_toolbox_emoji_naming.py`
- Create: `AgentBI/tests/test_toolbox_emoji_api.py`

**Interfaces:**
- Consumes: `{user_id, strategy, images:[{id,data_url}]}` with up to 16 images.
- Produces: `{names:[{id,name}], strategy, model}` where names are sanitized short Chinese strings.

- [ ] Write failing service tests for fenced JSON parsing, Chinese filename sanitization, missing vision route, batch call and per-image bounded concurrency.
- [ ] Write a failing API contract test for the naming endpoint.
- [ ] Add a reusable `ModelTaskService.complete_vision` method and implement batch/individual naming strategies.
- [ ] Register `/toolbox/emoji/name` and map configuration/upstream errors to readable responses.
- [ ] Run the targeted naming tests.

### Task 4: Browser-local sticker pipeline

**Files:**
- Create: `Agent-vue/src/api/toolbox-emoji-types.ts`
- Create: `Agent-vue/src/api/toolbox-emoji.ts`
- Create: `Agent-vue/src/toolbox/emoji-sticker.ts`
- Create: `Agent-vue/src/toolbox/emoji-sticker.test.ts`
- Modify: `Agent-vue/package.json`
- Modify mechanically: `Agent-vue/package-lock.json`

**Interfaces:**
- Produces: `buildStickerPrompt`, `detectStickerBounds`, `cutStickerSheet`, `downloadStickerZip` and naming API client.

- [ ] Add failing tests for prompt text toggle, style inclusion, corner-sampled background detection, component merge and safe Chinese filenames.
- [ ] Implement pure pixel/component helpers, then Canvas wrappers for transparent PNG extraction and outline rendering.
- [ ] Add JSZip and ZIP download support.
- [ ] Run toolbox unit tests.

### Task 5: Emoji Sticker Workbench UI

**Files:**
- Create: `Agent-vue/src/views/EmojiStickerView.vue`
- Modify: `Agent-vue/src/views/ToolboxView.vue`
- Modify: `Agent-vue/src/router/index.ts`

**Interfaces:**
- Consumes: shared `generateImage`, current chat preferences/provider, optional reference image and naming endpoint.
- Produces: `/toolbox/emoji` workflow with generation, cutting, naming, manual rename, preview and ZIP download.

- [ ] Build a printer-studio layout with left configuration rail, central sheet preview and right sticker tray.
- [ ] Add style presets, custom style, reference image preview/removal, default-on text and AI-name switches, and collapsed advanced parameters.
- [ ] Generate a square sheet with `scope_id=toolbox-emoji`, cut locally, then invoke Chinese naming.
- [ ] Add per-sticker download, editable name, remove, recut and ZIP download.
- [ ] Add the fifth Toolbox card and route.
- [ ] Run type-check, unit tests and production build.

### Task 6: Real naming strategy check and final verification

**Files:**
- Modify only if needed: `Agent-vue/src/views/EmojiStickerView.vue`
- Modify only if needed: `AgentBI/src/services/toolbox/emoji_naming.py`

**Interfaces:**
- Uses the current persisted `vision` route and a real generated sticker sheet.

- [ ] Generate/cut one representative sheet and call `strategy=batch` once.
- [ ] Compare returned Chinese names against visible stickers; if mapping is unreliable, switch the UI default to `individual` and verify concurrent requests.
- [ ] Run the full backend suite with `.\\venv\\python.exe -m unittest discover -s AgentBI/tests -v`.
- [ ] Run `npm run test:unit -- --run` and `npm run build` in `Agent-vue`.
- [ ] Review `git diff` and preserve unrelated Agnes/user changes.

## Self-review

- Spec coverage: reference image, Lite/Pro reuse, Image2, default text, Chinese naming, real naming test, advanced collapse, attachment library, previews, ZIP and styles all map to tasks above.
- Placeholder scan: no deferred implementation placeholders are present.
- Type consistency: `reference_image_data_url`, `scope_id`, `strategy`, `images`, `names` and `model` are consistent across API and UI boundaries.
