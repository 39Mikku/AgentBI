# Chat Workbench Design

## Goal

Add a post-login LLM chat workbench to the existing Vue and FastAPI project. It provides conversation history, OpenAI-compatible provider configuration, streamed answers, persisted context, and direct access to the existing email and MongoDB-query capabilities.

## Scope: phase one

- A desktop-first chat page with a collapsible conversation sidebar, message timeline, streaming composer, model selector, and settings page.
- Provider profiles stored in MongoDB without account-level authorization or per-account model permissions.
- Refreshing a provider's available models through its OpenAI-compatible `GET /models` endpoint.
- Per-user (currently the existing login email) conversations and messages in MongoDB.
- A configurable context-window measured in recent user/assistant turns.
- A streaming event protocol for answer text, visible execution summaries, tool status, errors, and completion.
- The existing `mongo_query` and `send_email` functions available to the chat agent for direct execution.

## Non-goals

- Authentication hardening, authorization, quotas, billing, multi-user provider permissions, file upload, image/video generation, Office editing, and background job queues.
- Exposing raw model chain-of-thought. Provider reasoning, when available, is normalized to a concise execution summary.

## Architecture

The existing `Agent-vue` and `AgentBI` applications remain the frontend and backend. The backend gains a chat service for persistence and streaming, a provider service for profiles and model discovery, and a main chat agent. Existing login code stays separate. MongoDB stores provider profiles, conversations, and messages; Redis remains limited to the existing login-code flow in this phase.

The browser talks only to FastAPI. FastAPI uses LiteLLM's Python SDK for OpenAI-compatible streaming calls, while provider model discovery is a direct authenticated request to each configured provider's `/models` endpoint. The selected profile controls model and temperature; the configured context-turn count controls the message window sent to the model.

## Data model

`provider_profiles`: name, base_url, api_key, available_models, default_model, created_at, updated_at.

`conversations`: user_id, title, provider_id, model, temperature, context_turns, created_at, updated_at, last_message_at.

`messages`: conversation_id, user_id, role (`user` or `assistant`), content, reasoning_summary, tool_events, status, created_at.

`user_id` is the login email supplied by the existing frontend state. It is an ownership label only in phase one; no authentication guarantee is implied.

## API and streaming contract

- `GET/POST/PATCH/DELETE /providers`: provider profile management.
- `POST /providers/{provider_id}/refresh-models`: call the configured `/models` endpoint and persist the returned model ids.
- `GET/POST/PATCH/DELETE /conversations`: per-user conversation list and metadata management.
- `GET /conversations/{conversation_id}/messages`: ordered history.
- `POST /chat/stream`: return `text/event-stream` events named `message_start`, `delta`, `reasoning_summary`, `tool_started`, `tool_finished`, `error`, and `done`.

Every event has JSON data containing `conversation_id`, `message_id` where applicable, and event-specific content. The frontend appends `delta` tokens into one assistant message and persists only when `done` is received.

## Agent and tool boundaries

`ChatAgent` owns the conversation-level system prompt and selects from a compact tool list. It calls the existing atomic `mongo_query` and `send_email` tools directly. Future multi-step functions (Office, database authoring, video) will be domain agents exposed to `ChatAgent` through a single high-level tool each; they are not part of phase one.

## UX

The post-login destination becomes `/chat`. The left sidebar lists conversations with create, rename, and delete actions. The main pane displays user, assistant, reasoning-summary, and tool-status blocks. The composer sends on Enter and inserts a newline with Shift+Enter. Generation is streamed and can be stopped. Settings is a separate route that manages providers and defaults; chat can override profile, model, temperature, and context turns for the active conversation.

## Validation

Backend unit tests cover Mongo repository serialization, model-list normalization, context slicing, and SSE event generation without calling external providers. Frontend tests or type checks cover API payloads and state transitions. The full frontend production build must pass. Backend import and route tests run with fakes for MongoDB, LiteLLM, and external tools.
