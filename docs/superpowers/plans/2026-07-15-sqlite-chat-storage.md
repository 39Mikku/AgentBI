# SQLite Chat Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the development chat persistence path with local SQLite while preserving the current conversation DAG, assistants, provider profiles, settings, and API contract.

**Architecture:** `SqliteChatRepository` becomes the single persistence implementation created by FastAPI at startup. It returns the same document-shaped dictionaries currently consumed by routes and schemas, with UUID strings in `_id` fields. MongoDB remains available only to the pre-existing login/email data-query tool; no Mongo chat data is imported or read.

**Tech Stack:** Python standard-library `sqlite3`, FastAPI, Pydantic, unittest.

## Global Constraints

- SQLite is the only chat database in development; do not import or dual-read old Mongo chat data.
- Preserve existing HTTP routes, SSE event shape, and chat DAG behavior.
- Do not stage or commit Git changes.
- Keep the login agent and email data-query Mongo integration unchanged.

---

### Task 1: Prove the desired SQLite repository behavior

**Files:**
- Create: `AgentBI/tests/test_sqlite_chat_repository.py`
- Create: `AgentBI/src/repositories/sqlite_chat_repository.py`

**Interfaces:**
- Produces `SqliteChatRepository(path: str)` with `create_conversation`, `create_user_message`, `create_assistant_message`, `complete_assistant_message`, `list_messages`, `retry_assistant_message`, and `get_active_path`.

- [x] **Step 1: Write failing repository tests**

```python
repository = SqliteChatRepository(":memory:")
assistant = repository.ensure_default_assistant("local-user")
thread = repository.create_conversation({"user_id": "local-user", "title": "Test", "assistant_id": assistant["_id"]})
user = repository.create_user_message(thread["_id"], "local-user", "Hello")
reply = repository.create_assistant_message(thread["_id"], "local-user", user["_id"])
repository.complete_assistant_message(reply["_id"], "Hi")
self.assertEqual([item["content"] for item in repository.get_active_path(thread["_id"], "local-user")], ["", "Hello", "Hi"])
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: FAIL because `sqlite_chat_repository` does not exist.

- [x] **Step 3: Implement schema and core DAG persistence**

Use UUID text primary keys, UTC ISO timestamps, foreign keys, indexes on `(user_id, last_message_at)`, `(thread_id, parent_id, created_at)`, and `(thread_id, sibling_group_id, created_at)`. Store JSON fields as text and deserialize them before returning documents.

- [x] **Step 4: Run repository tests to verify they pass**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: PASS.

### Task 2: Complete feature parity for current API consumers

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/tests/test_sqlite_chat_repository.py`

**Interfaces:**
- Produces all current repository operations: provider/profile/preferences CRUD, assistant CRUD, active version selection, edit/retry, branches, and message timeline persistence.

- [x] **Step 1: Write failing tests for assistant/profile/provider storage and branch versions**

```python
provider = repository.create_provider({"name": "Local", "base_url": "https://example.test/v1", "api_key": "key", "default_model": "demo"})
self.assertEqual(repository.update_provider(provider["_id"], {"available_models": ["demo", "demo-reasoner"]})["available_models"], ["demo", "demo-reasoner"])
edited = repository.edit_user_message(thread["_id"], "local-user", user["_id"], "Edited")
self.assertEqual(repository.get_sibling_versions(edited)[0]["role"], "user")
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: FAIL because one or more feature-parity methods are absent.

- [x] **Step 3: Implement only the missing public methods**

Implement the methods listed in `ChatRepository` with SQL queries and one transaction per logical write. `get_active_path` must use a recursive CTE, and `list_messages` must fetch sibling versions in one query rather than per-message remote-style lookups.

- [x] **Step 4: Run repository tests to verify they pass**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: PASS.

### Task 3: Switch FastAPI startup to SQLite

**Files:**
- Modify: `AgentBI/main.py`
- Modify: `AgentBI/src/api/dependencies.py`
- Modify: `AgentBI/src/services/chat_service.py`
- Modify: `AgentBI/src/services/provider_service.py`
- Test: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- `main.py` reads `CHAT_SQLITE_PATH` with default `AgentBI/data/agentbi.sqlite3` and initializes `SqliteChatRepository` unconditionally.

- [x] **Step 1: Write a failing startup contract test**

```python
with patch.dict(os.environ, {"CHAT_SQLITE_PATH": str(database_path)}, clear=False):
    async with lifespan(app):
        self.assertIsInstance(app.state.chat_repository, SqliteChatRepository)
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: FAIL because startup still constructs Mongo `ChatRepository`.

- [x] **Step 3: Switch imports and startup wiring**

Remove the Mongo chat client lifecycle from `main.py`; update repository type annotations to the SQLite implementation or a neutral protocol. Do not change `mongo_query_tool.py`.

- [x] **Step 4: Run backend suite and frontend build**

Run: `venv\python.exe -m unittest discover -s AgentBI\tests -v`

Run: `cd Agent-vue; npm run type-check; npm run build-only`

Expected: all tests and builds pass.
