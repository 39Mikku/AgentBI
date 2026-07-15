# Assistant Memory and Model Routing Design

## Goal

Extend the existing SQLite chat workbench with lightweight assistant-scoped long-term memory, model-decided semantic history search, optional conversation context compression, and first-turn model-generated titles.

## Boundaries

- Original `chat_messages` remain the source of truth and are never deleted or rewritten by compression.
- Core memory is one editable summary per user and assistant, injected into every request for that assistant when enabled.
- History search is a model tool named `search_assistant_history`; it is never forced on ordinary turns.
- Compression changes only the request context. Switching back to rolling-window mode immediately ignores the cached summary.
- Background models reuse configured provider profiles and never duplicate API keys.
- Model routes are user-scoped roles: `embedding`, `compression`, `memory`, and `title`. Chat model selection remains in chat preferences.

## Minimal Data

- `model_routes(user_id, role, provider_id, model, updated_at)`
- `assistant_memories(user_id, assistant_id, summary, last_summarized_message_id, updated_at)`
- `message_embeddings(message_id, user_id, assistant_id, model_key, vector, updated_at)`
- Assistant policy columns for memory, history search, and compression.
- Thread cache columns `context_summary` and `context_summary_until_message_id`.

## Runtime Flow

At request time, the active assistant core memory and valid thread summary are added to the system message. Rolling-window mode keeps the existing behavior. Compression mode keeps the configured recent turns and uses the cached summary for older messages.

When history search is enabled, `ChatAgent` exposes `search_assistant_history`. A tool call embeds the query, compares it with indexed messages from the same user and assistant, applies the configured cosine threshold, and returns at most the configured number of matches.

After a completed reply, a background maintenance task indexes the new messages, updates core memory only when the configured turn interval is reached, and refreshes the context summary when compression thresholds are reached. The first completed turn also invokes the title route and streams a `conversation_title_updated` event after persistence.

## UI

The model settings page adds four background model route selectors. The assistant editor adds memory enable/interval, current editable memory, history search enable/sensitivity/result limit, and compression strategy/threshold/recent-turn settings. Default assistant prompt remains hidden, but its operational policies remain configurable.

## Failure Handling

Missing routes disable only the dependent background feature. Failed background jobs preserve the previous memory, title, or context summary. History search returns a concise unavailable result instead of failing the main response. No background failure deletes messages.

## Verification

Backend tests cover repository persistence, cosine filtering, tool registration, memory interval decisions, compressed-context construction, and title events. Frontend type checking and production build cover the new settings contracts and controls.
