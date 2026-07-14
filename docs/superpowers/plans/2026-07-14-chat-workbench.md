# Chat Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first AgentBI LLM chat workbench with provider settings, MongoDB conversation persistence, streamed responses, and the existing email/Mongo tools.

**Architecture:** Keep the Vue and FastAPI applications. Add backend provider, chat persistence, stream, and agent modules; add Vue chat and settings routes, Pinia stores, and API clients. Use MongoDB for provider profiles, conversations, and messages; use LiteLLM SDK through an adapter for OpenAI-compatible streaming.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vue Router, Vite, FastAPI, Pydantic, PyMongo, LiteLLM, HTTPX, LangChain tools.

## Global Constraints

- Preserve the existing login flow and its Redis implementation.
- No account-level model authorization in phase one; use the login email as the user data key.
- Do not expose raw model chain-of-thought; emit concise reasoning summaries and tool statuses only.
- The browser communicates only with AgentBI; provider calls originate in AgentBI.
- Do not add image/video/Office/background-job implementations in this phase.

---

### Task 1: Backend configuration and schemas

**Files:**
- Create: `AgentBI/src/schemas/chat_schema.py`
- Create: `AgentBI/src/schemas/provider_schema.py`
- Modify: `AgentBI/src/models/llm_model.py`
- Modify: `AgentBI/requirements.txt`
- Test: `AgentBI/tests/test_schemas.py`

**Interfaces:**
- Produces `ProviderProfileCreate`, `ProviderProfileUpdate`, `ConversationCreate`, `ChatStreamRequest`, and `StreamEvent` Pydantic models.
- Produces `LLMModel.create_litellm_config(profile)` returning provider call arguments.

- [ ] Write schema tests for default temperature/context turns and rejected invalid ranges.
- [ ] Run `pytest AgentBI/tests/test_schemas.py -v` and verify failures before implementation.
- [ ] Implement schemas and a pinned dependency manifest containing FastAPI, Uvicorn, Pydantic, PyMongo, Redis, LangChain, langchain-openai, LiteLLM, HTTPX, and python-dotenv.
- [ ] Run the schema tests again and verify they pass.

### Task 2: Mongo chat repository and context assembly

**Files:**
- Create: `AgentBI/src/repositories/chat_repository.py`
- Create: `AgentBI/src/services/chat_service.py`
- Test: `AgentBI/tests/test_chat_repository.py`
- Test: `AgentBI/tests/test_chat_service.py`

**Interfaces:**
- Produces `ChatRepository(db)` methods `create_conversation`, `list_conversations`, `get_conversation`, `update_conversation`, `delete_conversation`, `list_messages`, and `append_message`.
- Produces `ChatService.build_context(conversation_id, context_turns)` returning chronological role/content messages.

- [ ] Write tests using a fake collection for user filtering, newest-first conversation sorting, message order, and context-turn slicing.
- [ ] Run the two test modules and verify failures before implementation.
- [ ] Implement repository methods with `ObjectId` string conversion at the API boundary and create indexes for `conversations(user_id,last_message_at)` and `messages(conversation_id,created_at)`.
- [ ] Implement context assembly: include the latest `context_turns * 2` persisted user/assistant messages.
- [ ] Run the two test modules and verify they pass.

### Task 3: Provider profiles and OpenAI-compatible model discovery

**Files:**
- Create: `AgentBI/src/services/provider_service.py`
- Create: `AgentBI/src/api/providers.py`
- Test: `AgentBI/tests/test_provider_service.py`
- Modify: `AgentBI/main.py`

**Interfaces:**
- Produces `ProviderService.refresh_models(provider_id)` which requests `{base_url}/models`, normalizes `data[].id`, and persists a sorted unique model list.
- Produces `/providers` CRUD and `/providers/{provider_id}/refresh-models` routes.

- [ ] Write tests with a fake HTTPX client for URL normalization, Bearer header usage, malformed model-list handling, and model-id deduplication.
- [ ] Run `pytest AgentBI/tests/test_provider_service.py -v` and verify failure before implementation.
- [ ] Implement the service and routes, inject the repository/database through app state, and register the router in `main.py`.
- [ ] Run the provider test module and verify it passes.

### Task 4: Chat agent, LiteLLM streaming, and SSE route

**Files:**
- Create: `AgentBI/src/agents/chat_agent.py`
- Create: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/src/services/chat_service.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_chat_stream.py`

**Interfaces:**
- Produces `ChatAgent.stream(messages, profile)` yielding normalized `delta`, `reasoning_summary`, `tool_started`, `tool_finished`, `error`, and `done` events.
- Produces `POST /chat/stream` as an SSE endpoint that persists user and complete assistant messages.

- [ ] Write fake-stream tests asserting SSE event names/order, incremental content assembly, persisted user/assistant messages, and surfaced provider failures.
- [ ] Run `pytest AgentBI/tests/test_chat_stream.py -v` and verify failure before implementation.
- [ ] Implement `ChatAgent` with the existing `mongo_query` and `send_email` tools registered for direct execution, and LiteLLM async streaming for provider output.
- [ ] Implement the SSE encoder and route with `StreamingResponse(media_type='text/event-stream')`; append a final `done` event only after persistence completes.
- [ ] Run the stream test module and verify it passes.

### Task 5: Conversation REST routes and frontend API clients

**Files:**
- Create: `AgentBI/src/api/conversations.py`
- Modify: `AgentBI/main.py`
- Create: `Agent-vue/src/api/chat.ts`
- Create: `Agent-vue/src/api/providers.ts`
- Create: `Agent-vue/src/api/chat-types.ts`
- Test: `AgentBI/tests/test_conversation_routes.py`

**Interfaces:**
- Produces conversation CRUD and message-history routes.
- Produces TypeScript `Conversation`, `ChatMessage`, `ProviderProfile`, `ChatPreferences`, and `ChatStreamEvent` interfaces.
- Produces `streamChat(request, handlers)` using `fetch` and SSE frame parsing.

- [ ] Write backend route tests with a fake repository for user-scoped list/create/update/delete behavior.
- [ ] Run the route test module and verify failure before implementation.
- [ ] Implement backend routes and TypeScript API modules; ensure all requests carry the current email as `user_id`.
- [ ] Run backend tests and `npm run type-check` in `Agent-vue`; verify both pass.

### Task 6: Vue chat state, routes, and first chat interface

**Files:**
- Create: `Agent-vue/src/stores/chat.ts`
- Create: `Agent-vue/src/views/ChatView.vue`
- Create: `Agent-vue/src/components/chat/ConversationSidebar.vue`
- Create: `Agent-vue/src/components/chat/MessageTimeline.vue`
- Create: `Agent-vue/src/components/chat/ChatComposer.vue`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/AboutView.vue`
- Test: `Agent-vue/src/stores/chat.spec.ts`

**Interfaces:**
- Produces a Pinia store exposing `loadConversations`, `createConversation`, `selectConversation`, `sendMessage`, `stopGeneration`, `renameConversation`, and `deleteConversation`.
- Produces `/chat` as the authenticated default route.

- [ ] Write store tests with mocked API functions for initial load, optimistic user message, delta concatenation, completion, and stream error.
- [ ] Run the frontend test command selected by the project after adding its test runner; verify it fails before implementation.
- [ ] Implement the store, route, and responsive three-region chat interface with conversation list, streaming message timeline, tool/reasoning blocks, and composer.
- [ ] Replace the post-login redirect destination from `/console` to `/chat` while keeping the existing console route accessible.
- [ ] Run the frontend store tests, `npm run type-check`, and `npm run build`; verify all pass.

### Task 7: Provider settings page and end-to-end verification

**Files:**
- Create: `Agent-vue/src/views/SettingsView.vue`
- Create: `Agent-vue/src/stores/providers.ts`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/assets/main.css`
- Modify: `Agent-vue/README.md`
- Modify: `AgentBI/开发文档.md`

**Interfaces:**
- Produces `/settings/models` with provider CRUD, connection test/model refresh, default-model selection, temperature, and context-turn controls.
- Produces persisted profile and active-conversation settings consumed by `ChatView`.

- [ ] Write provider-store tests with mocked provider API calls for model refresh and selected-model updates.
- [ ] Run the provider-store test and verify it fails before implementation.
- [ ] Implement the settings page and provider store, linking it from ChatView.
- [ ] Document required environment/configuration, Mongo collections, API routes, and local startup order.
- [ ] Run backend tests, frontend tests, `npm run type-check`, and `npm run build`; verify all pass.
