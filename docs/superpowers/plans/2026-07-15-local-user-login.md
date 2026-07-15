# Local User and Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move user profiles and email-code login entirely into the existing SQLite database, removing Redis, Mongo user lookup, and LLM orchestration from the login path.

**Architecture:** `SqliteChatRepository` owns `users` and `login_codes` alongside the existing chat tables. A deterministic `LoginService` resolves an existing username or accepts a first-time email, persists an expiring code, sends mail through a plain Python sender, and returns the canonical SQLite user record after verification. The mail subagent retains email sending but uses a restricted SQLite recipient lookup tool instead of generic Mongo querying.

**Tech Stack:** Python standard-library `sqlite3`, FastAPI, Pydantic, unittest, existing SMTP sender, Vue/Pinia.

## Global Constraints

- Do not import Mongo users or Redis codes; development starts with an empty local user database.
- First successful verification of an email creates a user whose initial username is the email prefix.
- Preserve `/send_code` and `/login` route paths, while returning a canonical `user_id` from successful login.
- Do not stage or commit Git changes.

---

### Task 1: Add local users and expiring login codes

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/tests/test_sqlite_chat_repository.py`

**Interfaces:**
- Produces `find_user`, `create_user`, `update_user`, `create_login_code`, and `consume_login_code`.

- [x] **Step 1: Write failing persistence tests**

```python
user = repository.create_user("elysi@example.com")
repository.create_login_code("elysi@example.com", "123456", "elysi@example.com")
self.assertEqual(repository.consume_login_code("elysi@example.com", "123456")["user_id"], user["user_id"])
```

- [x] **Step 2: Run the focused test and verify failure**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: FAIL because the local user/login-code API does not exist.

- [x] **Step 3: Implement the two SQLite tables and repository methods**

Create `users(user_id, username, email, avatar_data_url, created_at, updated_at)` with unique username/email indexes, and `login_codes(identity, code, target_email, expires_at)` keyed by identity. Delete a code when consumed; reject expired or mismatched codes.

- [x] **Step 4: Re-run the focused test**

Run: `venv\python.exe -m unittest AgentBI.tests.test_sqlite_chat_repository -v`

Expected: PASS.

### Task 2: Replace agent-driven login with a deterministic service

**Files:**
- Create: `AgentBI/src/services/login_service.py`
- Modify: `AgentBI/src/api/api.py`
- Modify: `AgentBI/src/tools/send_email_tool.py`
- Modify: `AgentBI/main.py`
- Create: `AgentBI/tests/test_login_service.py`

**Interfaces:**
- `LoginService.send_code(identity) -> dict`
- `LoginService.login(identity, code) -> dict | None`
- `send_email_message(to, subject, content) -> str`

- [x] **Step 1: Write failing service tests**

```python
service = LoginService(repository, sender=lambda *_: "ok", code_factory=lambda: "123456")
service.send_code("elysi@example.com")
self.assertEqual(service.login("elysi@example.com", "123456")["username"], "elysi")
```

- [x] **Step 2: Run the focused test and verify failure**

Run: `venv\python.exe -m unittest AgentBI.tests.test_login_service -v`

Expected: FAIL because `LoginService` does not exist.

- [x] **Step 3: Implement direct resolution, code generation, and SMTP dispatch**

Resolve known users by username or email; accept only an email for unknown identities. Remove `LoginAgent`, `redis`, and `MongoUserDirectory` from FastAPI startup and login routes. Preserve the LangChain email tool wrapper by making it call the new plain sender function.

- [x] **Step 4: Re-run the focused test**

Run: `venv\python.exe -m unittest AgentBI.tests.test_login_service -v`

Expected: PASS.

### Task 3: Use canonical local users in profile and frontend state

**Files:**
- Modify: `AgentBI/src/api/user_profile.py`
- Modify: `Agent-vue/src/api/types.ts`
- Modify: `Agent-vue/src/api/index.ts`
- Modify: `Agent-vue/src/stores/auth.ts`
- Modify: `AgentBI/tests/test_user_profile.py`

**Interfaces:**
- Successful `/login` returns `user_id`, `username`, and `email`.
- Pinia stores the returned `user_id`, not an arbitrary typed username.

- [x] **Step 1: Write failing response and state tests**

```python
response = UserProfileResponse.from_documents("elysi@example.com", {"username": "elysi", "email": "elysi@example.com"}, None)
self.assertEqual(response.username, "elysi")
```

- [x] **Step 2: Run backend and frontend checks**

Run: `venv\python.exe -m unittest discover -s AgentBI\tests -v`

Run: `cd Agent-vue; npm run type-check`

Expected: initially fail until the response and local identity handling are updated.

- [x] **Step 3: Switch profile lookup and canonical login storage**

Read profile data from `users`; persist returned `user_id` in `agentbi_user`; remove the Mongo directory dependency.

- [x] **Step 4: Run all verifications**

Run: `venv\python.exe -m unittest discover -s AgentBI\tests -v`

Run: `cd Agent-vue; npm run type-check; npm run build-only`

Expected: all tests and builds pass.
