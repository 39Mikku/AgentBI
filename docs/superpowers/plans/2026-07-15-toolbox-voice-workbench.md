# Toolbox Voice Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a non-agent Toolbox voice workbench for persistent user voice IDs, single-model synthesis, and optional multi-provider comparison across MiniMax, Bailian CosyVoice 3.5, MiMo V2.5 TTS, and Volcengine Seed TTS/ICL 2.0.

**Architecture:** FastAPI exposes a provider-neutral TTS capability/voice/synthesis API backed by injected provider adapters and the existing SQLite repository. Vue renders a Toolbox landing page and a two-column voice workbench with parameters on the left, text/results on the right; comparison mode issues independent synthesis requests and keeps audio only as browser Blob URLs.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, httpx, SQLite, Vue 3, Pinia, TypeScript, Vitest.

## Global Constraints

- Do not register Toolbox functions as Agent tools or subagents.
- Do not implement voice cloning, voice design, ASR, Live voice linkage, or generated-audio history.
- Persist only user-added voice metadata; never persist generated audio bytes or waveforms.
- Read provider credentials only from `AgentBI/.env`; never return secret values to the frontend.
- Keep Studio/Live mode navigation unchanged; Toolbox replaces the Studio sidebar capability button.
- Desktop layout is left parameters, right editor/results.
- Do not stage or commit changes; the user performs Git commits manually.

---

### Task 1: Environment Contract and TTS Domain Types

**Files:**
- Modify: `AgentBI/.env`
- Modify: `AgentBI/.env.example`
- Create: `AgentBI/src/schemas/toolbox_tts_schema.py`
- Create: `AgentBI/src/services/toolbox/__init__.py`
- Create: `AgentBI/src/services/toolbox/tts/__init__.py`
- Create: `AgentBI/src/services/toolbox/tts/base.py`
- Test: `AgentBI/tests/test_toolbox_tts_contract.py`

**Interfaces:**
- Produces: `TtsProviderId`, `TtsVoiceKind`, `TtsVoiceCreate`, `TtsVoiceUpdate`, `TtsSynthesisRequest`, `TtsSynthesisResult`, `TtsProviderAdapter`.
- Provider adapters expose `capability() -> dict` and `async synthesize(request) -> TtsSynthesisResult`.

- [ ] **Step 1: Add a failing contract test**

```python
def test_synthesis_request_rejects_empty_text(self):
    with self.assertRaises(ValidationError):
        TtsSynthesisRequest(user_id="alice", provider="minimax", model="speech-2.8-hd", voice_id="v", text=" ")
```

- [ ] **Step 2: Run the contract test and observe the missing module failure**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_contract`

- [ ] **Step 3: Implement strict Pydantic request/voice models and adapter protocol**

```python
class TtsSynthesisRequest(BaseModel):
    user_id: str
    provider: Literal["minimax", "bailian", "mimo", "volcengine"]
    model: str
    voice_id: str
    text: str = Field(min_length=1, max_length=10000)
    audio_format: Literal["mp3", "wav", "pcm"] = "mp3"
    parameters: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Add empty credential placeholders to both env files**

```dotenv
MINIMAX_API_KEY=
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
MIMO_API_KEY=
VOLCENGINE_TTS_APP_ID=
VOLCENGINE_TTS_ACCESS_TOKEN=
VOLCENGINE_TTS_RESOURCE_ID=
VOLCENGINE_ICL_RESOURCE_ID=
```

- [ ] **Step 5: Run the contract test and verify it passes**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_contract`

### Task 2: Persistent User Voice Catalog

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Test: `AgentBI/tests/test_toolbox_tts_repository.py`

**Interfaces:**
- Produces: `list_toolbox_tts_voices(user_id)`, `create_toolbox_tts_voice(payload)`, `update_toolbox_tts_voice(id, user_id, payload)`, `delete_toolbox_tts_voice(id, user_id)`.
- Voice dictionaries contain `id`, `user_id`, `provider`, `display_name`, `external_voice_id`, `voice_kind`, `bound_model`, `provider_metadata`, `created_at`, and `updated_at`.

- [ ] **Step 1: Add failing CRUD and ownership tests**

```python
voice = repository.create_toolbox_tts_voice({"user_id": "alice", "provider": "bailian", "display_name": "旁白", "external_voice_id": "cv-1", "voice_kind": "cloned", "bound_model": "cosyvoice-v3.5-plus"})
self.assertEqual(repository.list_toolbox_tts_voices("alice")[0]["id"], voice["id"])
self.assertIsNone(repository.update_toolbox_tts_voice(voice["id"], "bob", {"display_name": "x"}))
```

- [ ] **Step 2: Run the repository test and verify it fails**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_repository`

- [ ] **Step 3: Add the table, indexes, row mapping, and locked CRUD methods**

```sql
CREATE TABLE IF NOT EXISTS toolbox_tts_voices (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, provider TEXT NOT NULL,
  display_name TEXT NOT NULL, external_voice_id TEXT NOT NULL,
  voice_kind TEXT NOT NULL, bound_model TEXT,
  provider_metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS toolbox_tts_voices_by_user_provider
  ON toolbox_tts_voices(user_id, provider, updated_at DESC);
```

- [ ] **Step 4: Run the repository test and verify it passes**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_repository`

### Task 3: Provider Capability Registry

**Files:**
- Create: `AgentBI/src/services/toolbox/tts/registry.py`
- Test: `AgentBI/tests/test_toolbox_tts_registry.py`

**Interfaces:**
- Consumes: `TtsProviderAdapter` from Task 1.
- Produces: `TtsProviderRegistry.from_environment()`, `get(provider)`, `capabilities()`.
- Capability output includes provider label, configured state, missing env names, models, built-in voices, and parameter fields without secret values.

- [ ] **Step 1: Add failing fixed-model and missing-config tests**

```python
capabilities = registry.capabilities()
self.assertEqual([m["id"] for m in capabilities["bailian"]["models"]], ["cosyvoice-v3.5-plus", "cosyvoice-v3.5-flash"])
self.assertIn("MINIMAX_API_KEY", capabilities["minimax"]["missing_configuration"])
```

- [ ] **Step 2: Run the registry test and verify it fails**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_registry`

- [ ] **Step 3: Implement fixed provider manifests and configuration status**

The registry must expose only the model matrix approved in the design and must never inspect arbitrary OpenAI-compatible provider records.

- [ ] **Step 4: Run the registry test and verify it passes**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_registry`

### Task 4: Four Provider Adapters

**Files:**
- Create: `AgentBI/src/services/toolbox/tts/http.py`
- Create: `AgentBI/src/services/toolbox/tts/minimax.py`
- Create: `AgentBI/src/services/toolbox/tts/bailian_cosyvoice.py`
- Create: `AgentBI/src/services/toolbox/tts/mimo.py`
- Create: `AgentBI/src/services/toolbox/tts/volcengine.py`
- Test: `AgentBI/tests/test_toolbox_tts_adapters.py`

**Interfaces:**
- Consumes: validated `TtsSynthesisRequest`.
- Produces: normalized audio bytes, MIME type, extension, elapsed milliseconds, and safe provider metadata.
- HTTP transport is injectable so tests never call paid APIs.

- [ ] **Step 1: Add failing payload/response tests for all providers**

Verify MiniMax hex audio decoding, Bailian audio response decoding, MiMo OpenAI-compatible base64 audio decoding, Volcengine binary/base64 event decoding, fixed model validation, and sanitized upstream errors.

- [ ] **Step 2: Run adapter tests and verify missing implementations fail**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_adapters`

- [ ] **Step 3: Implement MiniMax and MiMo adapters with `httpx.AsyncClient`**

MiniMax calls `/v1/t2a_v2`; MiMo calls the OpenAI-compatible chat completions endpoint and reads `choices[0].message.audio.data`.

- [ ] **Step 4: Implement Bailian CosyVoice 3.5 and Volcengine Seed 2.0 adapters**

Keep provider authentication, resource IDs, request bodies, response decoding, and error-code mapping inside their adapter modules.

- [ ] **Step 5: Run adapter tests and verify they pass**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_adapters`

### Task 5: Toolbox TTS FastAPI Routes

**Files:**
- Create: `AgentBI/src/api/toolbox_tts.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_toolbox_tts_api.py`

**Interfaces:**
- Produces the six endpoints specified in the design.
- `POST /toolbox/tts/synthesize` returns audio bytes with `Content-Type`, `Content-Disposition`, `X-TTS-Provider`, `X-TTS-Model`, and `X-TTS-Elapsed-Ms` headers.

- [ ] **Step 1: Add failing capability, voice ownership, and binary response tests**

```python
response = client.post("/toolbox/tts/synthesize", json=request)
self.assertEqual(response.content, b"audio")
self.assertEqual(response.headers["content-type"], "audio/mpeg")
```

- [ ] **Step 2: Run route tests and verify failure**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_api`

- [ ] **Step 3: Implement routes with repository and registry dependency helpers**

Map missing voices to 404, ownership conflicts to 404, invalid provider/model combinations to 422, configuration errors to 503, and upstream errors to 502.

- [ ] **Step 4: Register the router in `AgentBI/main.py`**

- [ ] **Step 5: Run route tests and verify they pass**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_api`

### Task 6: Frontend API and Workbench Runtime

**Files:**
- Create: `Agent-vue/src/api/toolbox-tts-types.ts`
- Create: `Agent-vue/src/api/toolbox-tts.ts`
- Create: `Agent-vue/src/toolbox/voice-workbench.ts`
- Create: `Agent-vue/src/toolbox/voice-workbench.test.ts`
- Create: `Agent-vue/src/stores/toolbox-tts.ts`
- Create: `Agent-vue/src/stores/toolbox-tts.test.ts`

**Interfaces:**
- Produces typed capability/voice CRUD methods and `synthesizeTts()` returning `{ blob, metadata }`.
- Runtime supports one default lane, adding/removing/reordering comparison lanes, isolated lane errors, retries, and Blob URL cleanup.

- [ ] **Step 1: Add failing comparison and cleanup tests**

```typescript
await runtime.generateAll()
expect(runtime.lanes[0].status).toBe('success')
expect(runtime.lanes[1].status).toBe('error')
runtime.dispose()
expect(revokeObjectURL).toHaveBeenCalled()
```

- [ ] **Step 2: Run tests and verify missing runtime failure**

Run: `npm run test:unit -- src/toolbox/voice-workbench.test.ts src/stores/toolbox-tts.test.ts`

- [ ] **Step 3: Implement API decoding, store loading, lane generation, and cleanup**

- [ ] **Step 4: Run focused frontend tests and verify they pass**

Run: `npm run test:unit -- src/toolbox/voice-workbench.test.ts src/stores/toolbox-tts.test.ts`

### Task 7: Toolbox and Voice Workbench UI

**Files:**
- Create: `Agent-vue/src/views/ToolboxView.vue`
- Create: `Agent-vue/src/views/VoiceWorkbenchView.vue`
- Create: `Agent-vue/src/components/toolbox/VoiceSelector.vue`
- Create: `Agent-vue/src/components/toolbox/VoiceResultCard.vue`
- Create: `Agent-vue/src/components/toolbox/WaveformPreview.vue`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Test: `Agent-vue/src/toolbox/toolbox-navigation.test.ts`

**Interfaces:**
- `/toolbox` is the authenticated landing page.
- `/toolbox/voice` is the authenticated workbench.
- Chat sidebar Toolbox button routes to `/toolbox`.

- [ ] **Step 1: Add failing route/navigation mapping tests**

Verify route metadata and that the sidebar no longer routes its second utility button to capabilities.

- [ ] **Step 2: Run focused navigation test and verify failure**

Run: `npm run test:unit -- src/toolbox/toolbox-navigation.test.ts`

- [ ] **Step 3: Implement the Toolbox landing page and two-column workbench**

Use a dark editorial/technical visual system consistent with the product but distinct from chat. Keep parameters left and the large text editor plus result grid right. Comparison mode expands lanes in the left console and result cards in the right grid.

- [ ] **Step 4: Implement voice management and result components**

Voice management edits only metadata. Result cards use native audio playback plus a decoded or deterministic waveform preview and a Blob download link.

- [ ] **Step 5: Add routes and replace the Studio sidebar capability button**

- [ ] **Step 6: Run focused frontend tests, type-check, and build**

Run: `npm run test:unit -- src/toolbox/toolbox-navigation.test.ts`

Run: `npm run type-check`

Run: `npm run build-only`

### Task 8: Settings Navigation Polish and Full Verification

**Files:**
- Modify: `Agent-vue/src/views/SettingsView.vue`
- Modify: `Agent-vue/src/views/SubagentSettingsView.vue`

**Interfaces:**
- Both settings pages render the same top navigation geometry and responsive breakpoint behavior.

- [ ] **Step 1: Normalize settings navigation positioning and responsive styles**

Use the same right-aligned desktop placement, button height, spacing, active color, and mobile row placement in both pages.

- [ ] **Step 2: Run all backend tests**

Run: `.\venv\python.exe -m unittest discover -s AgentBI/tests -p "test_*.py"`

- [ ] **Step 3: Run all frontend tests, type-check, and production build**

Run: `npm run test:unit`

Run: `npm run type-check`

Run: `npm run build-only`

- [ ] **Step 4: Run changed-file lint, Python compile, and diff checks**

Run: `.\venv\python.exe -m compileall -q AgentBI/src`

Run: `git diff --check`

- [ ] **Step 5: With user-provided env values, make one short real synthesis request per provider**

Use a short neutral Chinese sentence, verify browser playback and download, and do not retain generated files after verification.
