# Test Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立于 Studio / Live 的 Test 模块，生成并持久化单选知识测试或趣味测试，支持逐题自动保存、确定性知识计分、结构化分析报告、历史重测和双 attempt 比较。

**Architecture:** Test 共享现有 `provider_profiles` 与 SQLite 文件，但使用独立 repository、schema、service、API、Pinia store 和页面。题目生成后不可变，历史结构为 session → attempts → answers；所有模型输出经过本地严格校验与最多一次修复，知识成绩只由 Python 计算。

**Tech Stack:** FastAPI、Pydantic v2、SQLite/WAL、OpenAI-compatible `AsyncOpenAI`、Vue 3、Pinia、Vue Router、Vitest、本地 SVG/CSS 图表。

## Global Constraints

- 只支持单选题；题量仅为 `5 | 10 | 15 | 20`，默认 10。
- 模型温度固定 `1.0`；模型响应 `max_tokens=16000`，文本最大 256 KiB。
- 额外要求可空；知识难度仅为 `beginner | intermediate | advanced`，默认 `intermediate`。
- Test 不调用 ChatAgent，不挂载工具、子代理、记忆、RAG 或 Live 协议。
- session/questionnaire API 永远返回公开裁剪题面；答案与解析只属于指定 completed attempt。
- 第一版趣味题不存在内部权重字段，未知字段由 `extra='forbid'` 拒绝。
- generation 与 analysis lease 都为 10 分钟，完成写入必须以 lease 做 CAS，迟到结果必须丢弃。
- LLM 调用期间绝不持有 SQLite 写事务。
- 用户手动提交 Git；所有任务不得 stage、commit 或 push。
- UI 采用“编辑部测评实验室”方向：深色仪器侧栏、暖纸主画布、钴蓝/酸性珊瑚模式色、大号题号和印刷式结果排版；不使用聊天气泡或通用渐变卡片。

---

## File Map

### Backend

- `AgentBI/src/schemas/test_schema.py`：Test 请求/响应、私有题库、公开题面、结果与图表 Pydantic schema。
- `AgentBI/src/services/test_structured_output.py`：单对象 JSON 提取、大小限制、严格校验和安全错误摘要。
- `AgentBI/src/services/test_scoring.py`：知识题确定性计分与知识点聚合。
- `AgentBI/src/repositories/sqlite_test_repository.py`：Test DDL、事务、幂等 request、lease、session/attempt/answer CRUD。
- `AgentBI/src/services/openai_compatible_client.py`：无业务含义的 OpenAI-compatible client factory。
- `AgentBI/src/services/test_model_service.py`：Test 双模型解析、出题/分析/修复的非流式调用。
- `AgentBI/src/services/test_service.py`：生成、公开裁剪、自动保存、提交、重试、超时恢复编排。
- `AgentBI/src/api/tests.py`：`/tests` 与 `/test-attempts` 路由。
- `AgentBI/main.py`：初始化 Test repository/service、回收 stale lease、注册 router、关闭连接。

### Frontend

- `Agent-vue/src/api/test-types.ts`：API DTO。
- `Agent-vue/src/api/tests.ts`：Test API client。
- `Agent-vue/src/test/test-domain.ts`：纯函数状态派生、attempt 比较、图表数据归一化。
- `Agent-vue/src/stores/test.ts`：Test 历史、创建、答题、自动保存、提交、轮询和偏好状态。
- `Agent-vue/src/components/test/TestModelSettings.vue`：双模型配置。
- `Agent-vue/src/components/test/TestCreatePanel.vue`：新测试表单。
- `Agent-vue/src/components/test/TestQuestionDeck.vue`：逐题单选与导航。
- `Agent-vue/src/components/test/TestChart.vue`：bar/radar/donut 本地渲染。
- `Agent-vue/src/components/test/TestResultReport.vue`：知识/趣味结果与失败恢复。
- `Agent-vue/src/components/test/TestAttemptCompare.vue`：两次 completed attempts 比较。
- `Agent-vue/src/views/TestView.vue`：页面编排和历史侧栏。
- `Agent-vue/src/router/index.ts`、`Agent-vue/src/components/AppModeSwitcher.vue`：产品入口。

---

### Task 1: Strict Test Domain Schemas, Parsing, and Scoring

**Files:**
- Create: `AgentBI/src/schemas/test_schema.py`
- Create: `AgentBI/src/services/test_structured_output.py`
- Create: `AgentBI/src/services/test_scoring.py`
- Create: `AgentBI/tests/test_test_schema.py`
- Create: `AgentBI/tests/test_test_structured_output.py`
- Create: `AgentBI/tests/test_test_scoring.py`

**Interfaces:**
- Produces: `TestMode`, `TestDifficulty`, `KnowledgeQuestionnaire`, `FunQuestionnaire`, `PublicQuestionnaire`, `KnowledgeAnalysis`, `FunAnalysis`, `ChartData`, `CreateTestRequest`, `ModelSnapshot`, `KnowledgeAnalysisInput`, `FunAnalysisInput`.
- Produces: discriminated attempt responses: draft/analyzing/failed expose only public questionnaire and current selections; completed knowledge exposes selected/correct option, correctness, explanation, knowledge points, deterministic score and `KnowledgeAnalysis`; completed fun exposes selections and `FunAnalysis`. Non-completed schema types do not define answer-key fields.
- Produces: `parse_structured_object(text: str, model_type: type[T]) -> T`.
- Produces: `safe_validation_summary(exc: Exception) -> str`.
- Produces: `score_knowledge_test(questionnaire, answers) -> KnowledgeScore`.

- [ ] **Step 1: Write failing schema tests**

```python
def test_fun_question_rejects_correct_answer_and_internal_weights(self):
    payload = self.fun_payload()
    payload["questions"][0]["correct_option_id"] = "a"
    with self.assertRaises(ValidationError):
        FunQuestionnaire.model_validate(payload)

def test_knowledge_question_requires_answer_inside_its_options(self):
    payload = self.knowledge_payload()
    payload["questions"][0]["correct_option_id"] = "missing"
    with self.assertRaises(ValidationError):
        KnowledgeQuestionnaire.model_validate(payload)

def test_public_questionnaire_drops_private_answer_fields(self):
    public = to_public_questionnaire(
        KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
    )
    self.assertNotIn("correct_option_id", public.model_dump_json())

def test_failed_attempt_schema_cannot_contain_answer_key(self):
    payload = self.failed_attempt_payload()
    payload["questionnaire"]["questions"][0]["correct_option_id"] = "a"
    with self.assertRaises(ValidationError):
        FailedAttemptDetailResponse.model_validate(payload)
```

- [ ] **Step 2: Run schema tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_schema -v`  
Expected: import failure because `test_schema.py` does not exist.

- [ ] **Step 3: Implement exact schema constraints**

Use discriminated knowledge/fun questionnaire models, `ConfigDict(extra="forbid")`, constrained strings/arrays, question and option id uniqueness validators, exact question count validation, chart limits, and two explicit analysis schemas. Keep private questionnaires separate from public DTOs; do not serialize private fields and then delete keys ad hoc.

- [ ] **Step 4: Write failing parser and scorer tests**

```python
def test_parser_accepts_one_fenced_object_but_rejects_two_objects(self):
    parsed = parse_structured_object('```json\n{"title":"T","summary":"S","sections":[{"heading":"H","body":"B"}],"charts":[]}\n```', FunAnalysis)
    self.assertEqual(parsed.title, "T")
    with self.assertRaises(StructuredOutputError):
        parse_structured_object('{"a":1}\n{"b":2}', FunAnalysis)

def test_parser_rejects_text_over_256_kib(self):
    with self.assertRaises(StructuredOutputTooLargeError):
        parse_structured_object("x" * (256 * 1024 + 1), FunAnalysis)

def test_score_is_deterministic_and_groups_knowledge_points(self):
    result = score_knowledge_test(self.questionnaire(), {"q1": "a", "q2": "b"})
    self.assertEqual((result.correct_count, result.score, result.max_score), (1, 50.0, 100.0))
    self.assertEqual(result.knowledge_points["Python"].correct, 1)
```

- [ ] **Step 5: Implement parser and scorer**

The parser must scan balanced JSON braces while respecting quoted strings, accept optional code fences/adjacent prose, require exactly one top-level object, enforce the byte limit before parsing, and convert raw decode/validation details into a short safe summary. The scorer must validate a complete answer map, never call a model, and round percentage scores consistently to two decimals.

- [ ] **Step 6: Verify Task 1**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_schema AgentBI.tests.test_test_structured_output AgentBI.tests.test_test_scoring -v`  
Expected: all Task 1 tests pass.

---

### Task 2: SQLite Test Repository and Lease-Safe State Transitions

**Files:**
- Create: `AgentBI/src/repositories/sqlite_test_repository.py`
- Create: `AgentBI/tests/test_sqlite_test_repository.py`

**Interfaces:**
- Consumes: serialized private/public/result models from Task 1.
- Produces: `SqliteTestRepository(path: str, clock: Callable[[], datetime] | None = None)`.
- Produces: `GenerationReservation(state: acquired | in_progress | completed | failed, acquired: bool, lease_id: str | None, test_id: str | None, error_message: str | None)`.
- Produces: `AnalysisReservation(state: acquired | in_progress | completed | failed, acquired: bool, lease_id: str | None, attempt: dict)`.
- Produces: `get_preferences`, `save_preferences`, `reserve_generation`, `get_generation_status`, `complete_generation`, `fail_generation`, `recover_stale_generations`.
- Produces: `list_sessions`, `get_session`, `delete_session`, `create_or_resume_attempt`, `get_attempt`, `save_answers`.
- Produces: `begin_analysis`, `complete_analysis`, `fail_analysis`, `recover_stale_analyses`.

- [ ] **Step 1: Write failing DDL and isolation tests**

```python
def test_preferences_and_sessions_are_scoped_by_user(self):
    self.repository.save_preferences("alice", self.preferences())
    self.assertIsNone(self.repository.get_preferences("bob"))

def test_list_uses_stable_updated_at_and_id_cursor(self):
    first = self.create_session("a", updated_at=self.now)
    second = self.create_session("b", updated_at=self.now)
    page = self.repository.list_sessions("alice", limit=1)
    self.assertEqual(page.items[0]["id"], max(first["id"], second["id"]))
    self.assertEqual(len(self.repository.list_sessions("alice", cursor=page.next_cursor, limit=1).items), 1)
```

- [ ] **Step 2: Run repository tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_sqlite_test_repository -v`  
Expected: import failure because the repository does not exist.

- [ ] **Step 3: Implement idempotent DDL and basic CRUD**

Create all six tables from the spec, foreign keys, indexes, partial unique active-attempt index, `RLock`, `row_factory`, WAL and NORMAL synchronous. Return plain dictionaries with decoded JSON fields. Every resource lookup must include `user_id`; unknown and cross-user resources return `None` rather than leaking existence.

- [ ] **Step 4: Add failing idempotency and lease tests**

```python
def test_generation_completion_requires_current_lease(self):
    lease = self.repository.reserve_generation("alice", "request-1")
    self.repository.recover_stale_generations(self.now + timedelta(minutes=11))
    replacement = self.repository.reserve_generation("alice", "request-1")
    self.assertFalse(self.repository.complete_generation("alice", "request-1", lease.lease_id, self.generated_bundle()))
    self.assertTrue(self.repository.complete_generation("alice", "request-1", replacement.lease_id, self.generated_bundle()))

def test_duplicate_generation_request_does_not_acquire_second_lease(self):
    first = self.repository.reserve_generation("alice", "request-1")
    duplicate = self.repository.reserve_generation("alice", "request-1")
    self.assertTrue(first.acquired)
    self.assertEqual((duplicate.acquired, duplicate.state), (False, "in_progress"))

def test_late_analysis_result_cannot_replace_new_run(self):
    old = self.repository.begin_analysis(self.attempt_id, "alice", "submit-1", self.answers(), self.model_snapshot())
    self.repository.recover_stale_analyses(self.now + timedelta(minutes=11))
    new = self.repository.begin_analysis(self.attempt_id, "alice", "retry-1", self.answers(), self.model_snapshot())
    self.assertFalse(self.repository.complete_analysis(self.attempt_id, old.lease_id, self.result()))
    self.assertTrue(self.repository.complete_analysis(self.attempt_id, new.lease_id, self.result()))

def test_submit_final_snapshot_blocks_late_autosave(self):
    self.repository.begin_analysis(self.attempt_id, "alice", "submit-1", self.final_answers(), self.model_snapshot())
    with self.assertRaises(TestAttemptConflictError):
        self.repository.save_answers(self.attempt_id, "alice", self.stale_answers())
```

- [ ] **Step 5: Implement short transactional transitions**

`reserve_generation` and `begin_analysis` return typed reservation outcomes. Only `acquired=True` allocates a UUID lease and authorizes model I/O; duplicates return `in_progress`, `completed`, or `failed` without execution rights. `complete_generation` performs lease CAS and atomically creates session + initial draft + completed idempotency record. `begin_analysis` atomically validates/upserts final answers, computes or accepts precomputed knowledge score, snapshots the current model, creates an analysis run keyed by `(attempt_id, request_id)`, and marks the attempt analyzing. Completion/failure update both attempt and run only when status and lease match. Stale recovery marks generation failed or analysis failed/abandoned after 10 minutes. Active analyzing sessions return conflict on delete.

- [ ] **Step 6: Verify Task 2**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_sqlite_test_repository -v`  
Expected: all repository tests pass.

---

### Task 3: Test Model Client and Structured Generation/Analysis

**Files:**
- Create: `AgentBI/src/services/openai_compatible_client.py`
- Create: `AgentBI/src/services/test_model_service.py`
- Modify: `AgentBI/src/services/model_task_service.py`
- Create: `AgentBI/tests/test_test_model_service.py`
- Modify: `AgentBI/tests/test_model_task_service.py`

**Interfaces:**
- Consumes: provider dictionaries from `SqliteChatRepository`, preferences from `SqliteTestRepository`, Task 1 schemas/parser.
- Produces: `create_openai_compatible_client(provider) -> AsyncOpenAI`.
- Produces: `TestModelService.generate_questionnaire(user_id: str, request: CreateTestRequest) -> tuple[KnowledgeQuestionnaire | FunQuestionnaire, ModelSnapshot]`.
- Produces: `TestModelService.analyze_knowledge(user_id: str, payload: KnowledgeAnalysisInput) -> tuple[KnowledgeAnalysis, ModelSnapshot]`.
- Produces: `TestModelService.analyze_fun(user_id: str, payload: FunAnalysisInput) -> tuple[FunAnalysis, ModelSnapshot]`.

- [ ] **Step 1: Write failing client/model tests**

```python
async def test_generation_uses_selected_test_model_temperature_one_and_no_tools(self):
    questionnaire, snapshot = await self.service.generate_questionnaire("alice", self.request())
    call = self.fake_client.calls[0]
    self.assertEqual(call["model"], "generator-model")
    self.assertEqual(call["temperature"], 1.0)
    self.assertEqual(call["max_tokens"], 16000)
    self.assertNotIn("tools", call)
    self.assertEqual(questionnaire.title, "Python 基础")
    self.assertNotIn("api_key", snapshot.model_dump())

async def test_invalid_json_gets_exactly_one_isolated_repair_call(self):
    self.fake_client.responses = ["not-json", self.valid_questionnaire_json()]
    await self.service.generate_questionnaire("alice", self.request())
    self.assertEqual(len(self.fake_client.calls), 2)
    self.assertIn("UNTRUSTED_MODEL_OUTPUT", self.fake_client.calls[1]["messages"][1]["content"])

async def test_generation_and_analysis_use_independent_models_and_bounded_repair(self):
    await self.service.generate_questionnaire("alice", self.request())
    await self.service.analyze_knowledge("alice", self.knowledge_input())
    await self.service.analyze_fun("alice", self.fun_input())
    self.assertEqual([call["model"] for call in self.fake_client.calls], ["generator-model", "analysis-model", "analysis-model"])
    self.assertTrue(all(call["temperature"] == 1.0 and "tools" not in call for call in self.fake_client.calls))

async def test_each_operation_repairs_once_then_raises_controlled_error(self):
    operations = [
        lambda: self.service.generate_questionnaire("alice", self.request()),
        lambda: self.service.analyze_knowledge("alice", self.knowledge_input()),
        lambda: self.service.analyze_fun("alice", self.fun_input()),
    ]
    for operation in operations:
        self.fake_client.responses = ["invalid", "still invalid"]
        before = len(self.fake_client.calls)
        with self.assertRaises(TestStructuredOutputError):
            await operation()
        self.assertEqual(len(self.fake_client.calls) - before, 2)

async def test_all_operations_reject_oversized_response_and_configuration_errors(self):
    for operation in (self.generation_operation, self.knowledge_operation, self.fun_operation):
        self.fake_client.responses = ["x" * (256 * 1024 + 1), "x" * (256 * 1024 + 1)]
        with self.assertRaises(TestStructuredOutputError):
            await operation()
    self.test_repository.save_preferences("alice", self.missing_provider_preferences())
    with self.assertRaises(TestModelConfigurationError):
        await self.service.generate_questionnaire("alice", self.request())
```

- [ ] **Step 2: Run model tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_model_service AgentBI.tests.test_model_task_service -v`  
Expected: missing Test model service/client factory.

- [ ] **Step 3: Extract the neutral client factory**

Move only AsyncOpenAI construction and `LLM_USER_AGENT` behavior into `create_openai_compatible_client`; make existing `ModelTaskService` call it without changing temperatures, prompts, role resolution, embedding behavior or exceptions. Keep its regression tests green.

- [ ] **Step 4: Implement Test model calls**

Resolve generation and analysis preferences independently, validate provider/model existence with a typed configuration error, build mode-specific system prompts from the exact schema limits, and call ordinary non-streaming `chat.completions`. On parse/validation failure, make one repair call with old output and safe validation summary inside explicit untrusted delimiters. Apply this to generation, knowledge analysis and fun analysis; second failure raises a controlled structured-output error. Enforce 256 KiB on every response. Return typed models plus a snapshot containing provider id/name, model, temperature and timestamp; never include API key. Preserve `ModelTaskService._client` as a compatibility wrapper around the neutral factory so existing monkeypatch tests remain valid.

- [ ] **Step 5: Verify Task 3**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_model_service AgentBI.tests.test_model_task_service -v`  
Expected: all focused tests pass.

---

### Task 4: Test Application Service

**Files:**
- Create: `AgentBI/src/services/test_service.py`
- Create: `AgentBI/tests/test_test_service.py`

**Interfaces:**
- Consumes: Tasks 1–3 repository, scoring and model services.
- Produces: `TestService.get_or_initialize_preferences`, `update_preferences`, `create_test`, `list_tests`, `get_test`, `delete_test`, `create_or_resume_attempt`, `get_attempt`, `save_answers`, `submit_attempt`, `retry_analysis`, `recover_stale_work`.

- [ ] **Step 1: Write failing generation and preference tests**

```python
async def test_first_preferences_copy_studio_once_then_stay_independent(self):
    first = self.service.get_or_initialize_preferences("alice")
    self.chat_repository.save_preferences("alice", {"provider_id": "other", "model": "other-model", "temperature": 1.0, "context_turns": 12})
    second = self.service.get_or_initialize_preferences("alice")
    self.assertEqual(first, second)

async def test_create_is_idempotent_and_never_exposes_answers(self):
    first = await self.service.create_test("alice", self.create_request("request-1"))
    second = await self.service.create_test("alice", self.create_request("request-1"))
    self.assertEqual(first.session.id, second.session.id)
    self.assertNotIn("correct_option_id", first.model_dump_json())
    self.assertEqual(self.model.generate_calls, 1)

async def test_duplicate_create_while_generation_runs_does_not_call_model_twice(self):
    self.model.block_generation = True
    first = asyncio.create_task(self.service.create_test("alice", self.create_request("request-1")))
    await self.model.generation_started.wait()
    duplicate = await self.service.create_test("alice", self.create_request("request-1"))
    self.assertEqual(duplicate.state, "generating")
    self.assertEqual(self.model.generate_calls, 1)
    self.model.release_generation.set()
    await first
```

- [ ] **Step 2: Run service tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_service -v`  
Expected: missing `TestService`.

- [ ] **Step 3: Implement preferences, generation, history and public DTO mapping**

Initialization reads Studio preferences only when no Test row exists. `create_test` reserves generation before model I/O, validates the typed result, and completes via lease CAS. List/detail methods never return private questionnaire JSON. Attempt creation returns an existing active attempt or creates a new one with request-id idempotency. Every state mutation updates `test_sessions.updated_at`.

- [ ] **Step 4: Add failing submit/retry/recovery tests**

```python
async def test_knowledge_submit_scores_before_analysis_and_model_cannot_override_score(self):
    result = await self.service.submit_attempt("alice", self.attempt_id, self.submit_request())
    self.assertEqual((result.score, result.max_score, result.correct_count), (50.0, 100.0, 1))
    self.assertNotIn("score", result.analysis.model_dump())

async def test_analysis_failure_keeps_answers_and_can_retry_with_new_model_snapshot(self):
    self.model.fail_analysis = True
    failed = await self.service.submit_attempt("alice", self.attempt_id, self.submit_request())
    self.assertEqual(failed.status, "failed")
    self.model.fail_analysis = False
    self.test_repository.save_preferences("alice", self.other_analysis_preferences())
    completed = await self.service.retry_analysis("alice", self.attempt_id, self.retry_request("retry-1"))
    self.assertEqual(completed.status, "completed")
    self.assertEqual(completed.analysis_model, "other-analysis-model")

async def test_late_completion_is_discarded_after_recovery_and_retry(self):
    old_call = asyncio.create_task(self.service.submit_attempt("alice", self.attempt_id, self.submit_request()))
    await self.model.analysis_started.wait()
    self.clock.advance(minutes=11)
    await self.service.get_attempt("alice", self.attempt_id)
    self.model.use_new_result = True
    replacement = await self.service.retry_analysis("alice", self.attempt_id, self.retry_request("retry-1"))
    self.model.release_old_analysis.set()
    await old_call
    final = await self.service.get_attempt("alice", self.attempt_id)
    self.assertEqual(final.result, replacement.result)

async def test_get_and_retry_recover_stale_analysis_without_restart(self):
    self.clock.advance(minutes=11)
    detail = await self.service.get_attempt("alice", self.attempt_id)
    self.assertEqual(detail.status, "failed")
    retried = await self.service.retry_analysis("alice", self.attempt_id, self.retry_request("retry-1"))
    self.assertIn(retried.status, {"analyzing", "completed"})
```

- [ ] **Step 5: Implement submit and recovery orchestration**

Submit passes the frontend’s complete answer snapshot into the repository transaction, scores knowledge locally, then calls the correct typed analysis method after commit only when the reservation says `acquired=True`; duplicates return in-progress or existing results. Completion/failure is conditional on lease. Retry takes `RetryAnalysisRequest(user_id, request_id)`, creates at most one run per request id with current analysis preferences, and applies the same reservation states. Safe errors preserve answers/score but discard raw model output. `get_attempt`, `retry_analysis`, `get_generation_status` and repeated `create_test` perform resource-scoped stale recovery before deciding state; `recover_stale_work` also handles both lease types at startup.

- [ ] **Step 6: Verify Task 4**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_service -v`  
Expected: all service tests pass.

---

### Task 5: FastAPI Contract and Application Wiring

**Files:**
- Create: `AgentBI/src/api/tests.py`
- Modify: `AgentBI/main.py`
- Create: `AgentBI/tests/test_test_api.py`

**Interfaces:**
- Consumes: `TestService`.
- Produces: all `/tests` and `/test-attempts` endpoints from the approved spec.

- [ ] **Step 1: Write failing API tests**

```python
def test_create_accepts_empty_requirements_and_returns_public_questions(self):
    response = self.client.post("/tests", json=self.create_payload(requirements=""))
    self.assertEqual(response.status_code, 201)
    self.assertNotIn("correct_option_id", response.text)

def test_submit_requires_complete_snapshot_and_is_idempotent(self):
    first = self.client.post(f"/test-attempts/{self.attempt_id}/submit", json=self.submit_payload("submit-1"))
    second = self.client.post(f"/test-attempts/{self.attempt_id}/submit", json=self.submit_payload("submit-1"))
    self.assertEqual(first.json(), second.json())

def test_cross_user_resource_is_404_and_active_analysis_delete_is_409(self):
    self.assertEqual(self.client.get(f"/tests/{self.test_id}?user_id=bob").status_code, 404)
    self.assertEqual(self.client.delete(f"/tests/{self.test_id}?user_id=alice").status_code, 409)

def test_running_generation_returns_202_and_status_endpoint_recovers_stale_lease(self):
    running = self.client.post("/tests", json=self.create_payload(request_id="request-1"))
    self.assertEqual(running.status_code, 202)
    self.clock.advance(minutes=11)
    status_response = self.client.get("/tests/creation-requests/request-1?user_id=alice")
    self.assertEqual(status_response.json()["state"], "failed")

def test_preferences_get_put_and_stable_cursor_mode_filter(self):
    self.assertEqual(self.client.put("/tests/preferences", json=self.preferences_payload()).status_code, 200)
    self.assertEqual(self.client.get("/tests/preferences?user_id=alice").status_code, 200)
    first = self.client.get("/tests?user_id=alice&mode=knowledge&limit=1").json()
    second = self.client.get(f"/tests?user_id=alice&mode=knowledge&limit=1&cursor={quote(first['next_cursor'])}").json()
    self.assertTrue(all(item["mode"] == "knowledge" for item in first["items"] + second["items"]))
    self.assertFalse({item["id"] for item in first["items"]} & {item["id"] for item in second["items"]})

def test_retest_reuses_exact_questionnaire_and_only_completed_discloses_answers(self):
    original = self.client.get(f"/tests/{self.test_id}?user_id=alice").json()["questionnaire"]
    retest = self.client.post(f"/tests/{self.test_id}/attempts", json=self.retest_payload()).json()
    self.assertEqual(retest["questionnaire"], original)
    draft = self.client.get(f"/test-attempts/{self.attempt_id}?user_id=alice")
    self.assertNotIn("correct_option_id", draft.text)
    completed = self.complete_knowledge_attempt(self.attempt_id)
    self.assertIn("correct_option_id", completed.text)
    self.assertIn("explanation", completed.text)

def test_duplicate_submit_and_retry_do_not_add_runs_or_model_calls(self):
    before = self.fake_service.analysis_calls
    first = self.client.post(f"/test-attempts/{self.attempt_id}/submit", json=self.submit_payload("submit-1"))
    second = self.client.post(f"/test-attempts/{self.attempt_id}/submit", json=self.submit_payload("submit-1"))
    self.assertEqual(first.json(), second.json())
    self.assertEqual(self.fake_service.analysis_calls - before, 1)
    failed_id = self.make_failed_attempt()
    self.client.post(f"/test-attempts/{failed_id}/retry-analysis", json=self.retry_payload("retry-1"))
    self.client.post(f"/test-attempts/{failed_id}/retry-analysis", json=self.retry_payload("retry-1"))
    self.assertEqual(self.repository.count_analysis_runs(failed_id, "retry-1"), 1)

def test_failed_generation_requires_explicit_retry_flag(self):
    failed = self.make_failed_generation("request-1")
    blocked = self.client.post("/tests", json=self.create_payload(request_id=failed.request_id, retry_failed=False))
    retried = self.client.post("/tests", json=self.create_payload(request_id=failed.request_id, retry_failed=True))
    self.assertEqual(blocked.status_code, 409)
    self.assertIn(retried.status_code, {201, 202})
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_api -v`  
Expected: route/import failure.

- [ ] **Step 3: Implement router and error mapping**

Use app-state dependency injection for tests. Return 201 for a newly created test; 202 plus typed status and polling URL when generation/analysis is already in progress; 200 for idempotently recovered completed/failed results; 204 for delete; 404 for unknown/cross-user; 409 for state or model-configuration conflicts, failed generation without explicit retry, deleted provider or empty model; 422 for validation/incomplete answers; 502 for upstream/structured-output failure during generation; and 500 only for unexpected local failures. Analysis failures are persisted and returned as typed failed attempt responses rather than raw exceptions. Never include raw upstream payloads in HTTP details. Cover preferences GET/PUT, stable cursor + mode filter, draft-only autosave, retest questionnaire identity, completed-only answer disclosure, retry-analysis, generation status/retry, and duplicate submit/retry request ids.

- [ ] **Step 4: Wire lifecycle**

Initialize `SqliteTestRepository` with the same `CHAT_SQLITE_PATH`, create `TestService` from Test + chat repositories, call stale recovery at startup, register the router, and close Test repository during shutdown. Preserve existing music process and repository lifecycle order.

- [ ] **Step 5: Verify Task 5 and backend regression**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_test_api -v`  
Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`  
Expected: focused and full backend suites pass.

---

### Task 6: Frontend Test API, Domain Helpers, and Pinia Store

**Files:**
- Create: `Agent-vue/src/api/test-types.ts`
- Create: `Agent-vue/src/api/tests.ts`
- Create: `Agent-vue/src/test/test-domain.ts`
- Create: `Agent-vue/src/test/test-domain.test.ts`
- Create: `Agent-vue/src/stores/test.ts`
- Create: `Agent-vue/src/stores/test.test.ts`

**Interfaces:**
- Produces: typed API functions matching Task 5.
- Produces: `remainingQuestionCount`, `nextUnansweredIndex`, `normalizeChart`, `compareAttempts`.
- Produces: `useTestStore()` actions for preferences/history/create/generation-status polling/explicit failed-generation retry/open/answer/submit/retry/retest/delete/compare.

- [ ] **Step 1: Write failing pure-domain tests**

```typescript
it('finds unanswered questions and does not mutate the answer map', () => {
  const answers = { q1: 'a' }
  expect(remainingQuestionCount(['q1', 'q2'], answers)).toBe(1)
  expect(nextUnansweredIndex(['q1', 'q2'], answers)).toBe(1)
  expect(answers).toEqual({ q1: 'a' })
})

it('compares knowledge attempts by score and changed answers', () => {
  const result = compareAttempts(knowledgeAttempt(60), knowledgeAttempt(80))
  expect(result.scoreDelta).toBe(20)
  expect(result.changedQuestions).toContain('q2')
})

it('aligns common and unmatched dimensions for fun attempt comparison', () => {
  const result = compareAttempts(funAttempt({ curiosity: 80, calm: 40 }), funAttempt({ curiosity: 60, energy: 90 }))
  expect(result.common.map((item) => item.label)).toEqual(['curiosity'])
  expect(result.leftOnly.map((item) => item.label)).toEqual(['calm'])
  expect(result.rightOnly.map((item) => item.label)).toEqual(['energy'])
})

it('keeps different fun chart kinds in separate comparison groups', () => {
  const result = compareAttempts(funAttemptWithChart('radar'), funAttemptWithChart('bar'))
  expect(result.common).toEqual([])
  expect(result.leftOnly).toHaveLength(1)
  expect(result.rightOnly).toHaveLength(1)
})

it('renders zero-valued chart inputs without division by zero', () => {
  expect(normalizeChart({ kind: 'radar', title: 'Empty', items: [{ label: 'A', value: 0, max_value: 0 }, { label: 'B', value: 0, max_value: 0 }] }).items.every((item) => Number.isFinite(item.ratio))).toBe(true)
  expect(normalizeChart({ kind: 'donut', title: 'Empty', items: [{ label: 'A', value: 0, max_value: 100 }, { label: 'B', value: 0, max_value: 100 }] }).total).toBe(0)
})
```

- [ ] **Step 2: Run frontend domain tests and verify RED**

Run: `npm run test:unit -- src/test/test-domain.test.ts` from `Agent-vue`  
Expected: missing module.

- [ ] **Step 3: Implement DTOs, API client and pure helpers**

Use the project’s existing API base URL/error conventions. Generate UUID request ids in the caller and reuse them on retried HTTP requests. `normalizeChart` must reject unknown kind, non-finite/out-of-range values and length mismatches even though the backend already validates them.

- [ ] **Step 4: Write failing store tests**

```typescript
it('autosaves the selected answer but submit sends the complete local snapshot', async () => {
  store.selectAnswer('q1', 'a')
  store.selectAnswer('q2', 'b')
  await store.flushAutosave()
  await store.submitCurrentAttempt()
  expect(api.submitAttempt).toHaveBeenCalledWith(expect.objectContaining({
    answers: [{ question_id: 'q1', selected_option_id: 'a' }, { question_id: 'q2', selected_option_id: 'b' }],
  }))
})

it('polls analyzing attempt and exposes retry when it becomes failed', async () => {
  api.getAttempt.mockResolvedValueOnce(analyzingAttempt()).mockResolvedValueOnce(failedAttempt())
  await store.resumeAttempt('attempt-1')
  await vi.runAllTimersAsync()
  expect(store.currentAttempt?.status).toBe('failed')
  expect(store.canRetryAnalysis).toBe(true)
})

it('stopPolling cancels pending attempt refreshes', async () => {
  store.startPolling('attempt-1')
  store.stopPolling()
  await vi.runAllTimersAsync()
  expect(api.getAttempt).not.toHaveBeenCalled()
})

it('polls a 202 generation to completed and opens the generated test', async () => {
  api.createTest.mockResolvedValue(generatingStatus('request-1'))
  api.getGenerationStatus.mockResolvedValueOnce(generatingStatus('request-1')).mockResolvedValueOnce(completedGeneration('test-1'))
  await store.createTest(createPayload('request-1'))
  await vi.runAllTimersAsync()
  expect(store.currentSession?.id).toBe('test-1')
  expect(store.generationState).toBe('completed')
})

it('keeps failed generation request and retries only with retry_failed true', async () => {
  api.getGenerationStatus.mockResolvedValue(failedGeneration('request-1'))
  await store.resumeGeneration('request-1')
  await store.retryFailedGeneration()
  expect(api.createTest).toHaveBeenCalledWith(expect.objectContaining({ request_id: 'request-1', retry_failed: true }))
})
```

- [ ] **Step 5: Implement Pinia state machine**

Debounce autosave, expose `saveState: idle | saving | saved | error`, retain failed local changes, and let explicit retry flush them. Submit first flushes/uses current local map, sends a complete sorted snapshot, disables duplicate submission, and replaces state with server truth. Resume draft answers after refresh; expose `startPolling(attemptId)`, `startGenerationPolling(requestId)`, and one `stopPolling()` that cancels both timers. A 202 create persists the request id, polls generation status, opens the completed test, or retains the failed request and safe error until the user explicitly retries with `retry_failed=true`. Poll analyzing attempts at a bounded interval and stop on completed/failed. Preserve Test model preferences independently.

- [ ] **Step 6: Verify Task 6**

Run: `npm run test:unit -- src/test/test-domain.test.ts src/stores/test.test.ts` from `Agent-vue`  
Expected: all Task 6 tests pass.

---

### Task 7: Distinctive Test UI, Charts, Results, and Product Navigation

**Files:**
- Create: `Agent-vue/src/components/test/TestModelSettings.vue`
- Create: `Agent-vue/src/components/test/TestCreatePanel.vue`
- Create: `Agent-vue/src/components/test/TestQuestionDeck.vue`
- Create: `Agent-vue/src/components/test/TestChart.vue`
- Create: `Agent-vue/src/components/test/TestResultReport.vue`
- Create: `Agent-vue/src/components/test/TestAttemptCompare.vue`
- Create: `Agent-vue/src/views/TestView.vue`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/components/AppModeSwitcher.vue`
- Modify: `Agent-vue/src/views/ChatView.vue` only if the three-item switcher needs width adjustment at its call site.
- Modify: `Agent-vue/src/views/LiveView.vue` only if the three-item switcher needs width adjustment at its call site.

**Interfaces:**
- Consumes: Task 6 store, helpers and DTOs.
- Produces: `/test` user experience and Studio / Live / Test navigation.

- [ ] **Step 1: Extend route and product switcher**

Add `{ path: '/test', name: 'test', component: () => import('@/views/TestView.vue'), meta: { title: 'Test Lab · AgentBI', requiresAuth: true } }`. Extend switcher prop to `'studio' | 'live' | 'test'`, add index `03`, and use a three-column grid without shrinking labels below readability.

- [ ] **Step 2: Implement the visual system and responsive shell**

Build a fixed-height app shell with independently scrolling dark history rail and warm-paper main canvas so page scrolling cannot stretch the sidebar or displace the header. Use CSS variables for ink/paper/cobalt/coral, distinctive editorial display/body typography already available in the project, fine rules, numbered states and grain. Add `@media (prefers-reduced-motion: reduce)` and mobile history drawer behavior.

- [ ] **Step 3: Implement creation and question flow**

Creation panel must expose mode, topic, count, conditional knowledge difficulty, optional requirements and generation loading. Question deck renders one question at a time with large serial number, progress rail, answered markers, previous/next, keyboard-accessible radio controls, autosave status, remaining count and final submit guard.

- [ ] **Step 4: Implement model settings and history recovery states**

Model settings uses existing provider/model catalogs but has separate generation and analysis selectors. History shows mode, title, attempt count, status and recent activity; opening restores draft answers, polls analyzing, or displays a safe failed state with retry. Creation state persists the current request id while polling a 202 generation, resumes polling after page state reload, and shows an explicit failed-generation retry action that reuses the id with `retry_failed=true`. Disable delete while analyzing and explain why.

`TestView` must call `store.stopPolling()` from `onBeforeUnmount`. Chart rendering must treat radar `max_value=0` as ratio 0 and donut total 0 as an explicit empty ring, never divide by zero or emit non-finite SVG attributes.

- [ ] **Step 5: Implement native charts, report, and attempt comparison**

Render bar with semantic lists/CSS widths, donut with SVG stroke dash arrays, and radar with computed polygon points and labeled axes. Never use `v-html` for model data. Knowledge report includes deterministic score, correct count, knowledge-point accuracy, per-question explanation and model narrative. Fun report includes conclusion, sections and up to two charts. Comparison allows exactly two completed attempts and renders score/question deltas or common/unmatched fun dimensions.

- [ ] **Step 6: Verify Task 7**

Run: `npm run test:unit` from `Agent-vue`  
Run: `npm run type-check` from `Agent-vue`  
Run: `npm run build-only` from `Agent-vue`  
Expected: all frontend tests, type-check and production build pass.

---

### Task 8: Full Regression and Local Smoke Verification

**Files:**
- Modify only files required to fix issues proven by this task’s verification.
- Create: `.superpowers/sdd/test-module-verification.md`

**Interfaces:**
- Consumes: completed Tasks 1–7.
- Produces: repeatable verification evidence; no Git commit.

- [ ] **Step 1: Run full backend suite**

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`  
Expected: all backend tests pass.

- [ ] **Step 2: Run full frontend verification**

Run: `npm run test:unit` from `Agent-vue`  
Run: `npm run type-check` from `Agent-vue`  
Run: `npm run build-only` from `Agent-vue`  
Expected: all frontend checks pass.

- [ ] **Step 3: Run API smoke with fake model service**

Use FastAPI dependency override and a temporary SQLite path to prove: empty requirements create succeeds; public creation response has no answer keys; autosave survives reload; submit returns deterministic knowledge score; fun result charts validate; same request id is idempotent; stale lease and late result cannot overwrite a replacement run; retest reuses the same questionnaire; two completed attempts remain independently readable.

- [ ] **Step 4: Run browser smoke in Chrome only**

Use the user-requested Chrome integration, not the Codex in-app browser. Verify desktop and narrow viewport: Test appears beside Studio/Live; history rail stays fixed; creation, one-question navigation, autosave status, submit loading, result charts, failed retry, refresh recovery, retest and attempt comparison are usable; no console errors occur.

- [ ] **Step 5: Record evidence and inspect working tree**

Write exact commands/counts and smoke observations to `.superpowers/sdd/test-module-verification.md`. Run `git diff --check` and `git status --short`. Do not stage, commit or push.
