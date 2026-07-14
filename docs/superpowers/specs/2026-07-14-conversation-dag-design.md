# Conversation DAG Design

## Goal

Replace the phase-one linear chat history with a MongoDB-backed message DAG. It must support immutable user-message edits, assistant retries, version switching, and creating a new independent conversation from any message.

## Chosen design

The application keeps MongoDB as the concrete persistence implementation, but only the chat repository contains PyMongo and ObjectId details. The API and `ChatService` use thread, message-node, active-head, and run concepts.

- `chat_threads` stores user ownership, presentation/configuration fields, `active_message_id`, and optional source-thread/source-message provenance.
- `chat_messages` is an adjacency-list DAG. Every content message has `parent_id`; a thread has one unrendered `root` node with `parent_id = null`.
- `chat_runs` records the provider/model/temperature/context snapshot and streaming result for each generated assistant message.
- Retry creates an assistant sibling below the same user parent. Editing creates a user sibling below the same parent. Both update the thread active head atomically.
- A branch conversation is a new thread with copied ancestors through the selected source message. It records provenance but never shares message nodes with the source thread.

## Context and UI

The active path is the chain from `active_message_id` to the thread root, ordered root-to-leaf and limited by configured context turns. Only that chain is sent to the model. Siblings are returned alongside the active path so the client can render version arrows without mixing alternate replies into context.

The existing `/conversations` API name remains during this migration to avoid unrelated frontend routing changes, but its backing store becomes `chat_threads`. Message responses gain `parent_id`, `sibling_group_id`, and sibling-position metadata.

## Safety and rollout

Phase-one `conversations` and `messages` collections are left untouched. New code reads and writes only `chat_threads`, `chat_messages`, and `chat_runs`. Index creation is idempotent. No automatic deletion or conversion runs because existing data does not need to be retained.

## Validation

Backend tests cover active-path construction, sibling creation, edit/retry semantics, branch copying, and route exposure. Frontend type checking and production build validate API/state/UI integration.
