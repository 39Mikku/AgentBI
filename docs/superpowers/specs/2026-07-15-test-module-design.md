# Test 模块设计规格

日期：2026-07-15  
状态：已确认设计，待实施

## 1. 目标

在现有 Studio、Live 之外新增独立的 Test 产品模块。用户给定主题与可选要求，由大模型生成结构化单选测试；用户逐题作答并一次性提交完整答卷；系统再调用分析模型生成结果报告。

Test 支持两种模式：

- 知识测试：题目有确定正确答案，服务端计算成绩，模型只分析掌握情况、薄弱点与学习建议。
- 趣味测试：题目无正确答案，模型根据完整答卷生成结论、详细说明和受控图表数据。

该模块保存历史测试与每次作答，但不复用 Studio 消息 DAG、助手、工具、子代理、记忆或 Live 实时音频协议。

## 2. 已确认的产品决策

- 所有题目均为单选题。
- 新测试始终创建新的测试会话，并调用模型生成一套新题。
- 历史测试的“重新测试”复用原始题目，不重新生成。
- 同一测试可保留多次作答记录，并可切换查看和比较。
- 题量可选 5、10、15、20，默认 10。
- 知识测试可选择难度。
- 主题必填；额外要求可留空。
- 答题页一次展示一题，允许前后切换，全部完成后统一提交。
- 用户选择自动保存在当前 draft attempt，不提供多余的手动“保存”操作。
- Test 复用已有供应商和模型目录，但独立保存出题模型与结果分析模型。
- 首次初始化 Test 配置时可继承 Studio 当前供应商和模型一次；此后互不跟随。
- 模型温度统一使用项目现行约定 `1.0`，不自行降低温度。
- 历史“重新测试”定位为自我复习而非防作弊考试；用户可以主动打开旧的 completed attempt 查看答案，但当前 draft 的 API 不得主动夹带答案。

## 3. 模块边界

### 3.1 复用

- `provider_profiles` 中的 OpenAI-compatible `base_url`、`api_key`、模型目录。
- 当前登录用户标识与前端路由守卫。
- 现有 SQLite 文件、连接参数和 WAL 模式。
- 现有应用视觉 token、字体与顶部产品模式切换组件。

### 3.2 独立

- 独立 Test repository，不向 `SqliteChatRepository` 继续堆叠 Test 领域方法。
- 独立 Test service、schema、API、Pinia store 和页面组件。
- 独立的出题模型和分析模型配置。
- 独立历史列表，不伪装成 `/conversations`、`chat_threads` 或 `live_threads`。

### 3.3 明确不做

- 不调用 ChatAgent，不挂载工具或子代理。
- 不使用 Studio 的上下文、记忆、RAG、助手提示词或 SSE 流。
- 不使用 Live 的角色、音色、WebSocket 或实时消息。
- 第一阶段不支持多选、填空、判断、主观题和题目编辑。
- 不让模型返回可执行 HTML、SVG、JavaScript 或任意图表配置。

## 4. 核心数据模型

Test 与现有业务共享同一个 SQLite 文件，但使用独立表和独立 repository 类。

### 4.1 `test_preferences`

- `user_id TEXT PRIMARY KEY`
- `generation_provider_id TEXT NULL`
- `generation_model TEXT NULL`
- `analysis_provider_id TEXT NULL`
- `analysis_model TEXT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

若用户尚无 Test 配置，服务读取 Studio 当前 provider/model 作为一次性默认值并创建 Test 配置。供应商或模型失效时，前端提示重新选择，不静默回退到其他模型。

### 4.2 `test_sessions`

- `id TEXT PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `mode TEXT NOT NULL CHECK(mode IN ('knowledge', 'fun'))`
- `topic TEXT NOT NULL`
- `requirements TEXT NOT NULL DEFAULT ''`
- `title TEXT NOT NULL`
- `description TEXT NOT NULL DEFAULT ''`
- `question_count INTEGER NOT NULL CHECK(question_count IN (5, 10, 15, 20))`
- `difficulty TEXT NULL`
- `questionnaire_json TEXT NOT NULL`
- `schema_version INTEGER NOT NULL DEFAULT 1`
- `generation_provider_id TEXT NOT NULL`
- `generation_model TEXT NOT NULL`
- `generation_snapshot_json TEXT NOT NULL`
- `create_request_id TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

`difficulty` 仅允许 `beginner | intermediate | advanced`，知识测试默认 `intermediate`，趣味测试必须为 `NULL`。题目成功生成并通过校验后即不可变。`generation_snapshot_json` 只保存 provider id/name、model、temperature 和生成时间，不保存 API key。`UNIQUE(user_id, create_request_id)` 关联新建请求的幂等结果。

### 4.3 `test_attempts`

- `id TEXT PRIMARY KEY`
- `test_id TEXT NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE`
- `user_id TEXT NOT NULL`
- `status TEXT NOT NULL CHECK(status IN ('draft', 'analyzing', 'completed', 'failed'))`
- `score REAL NULL`
- `max_score REAL NULL`
- `correct_count INTEGER NULL`
- `result_json TEXT NULL`
- `analysis_provider_id TEXT NULL`
- `analysis_model TEXT NULL`
- `analysis_snapshot_json TEXT NULL`
- `submission_token TEXT NULL UNIQUE`
- `create_request_id TEXT NOT NULL`
- `error_message TEXT NULL`
- `analysis_started_at TEXT NULL`
- `analysis_lease_id TEXT NULL`
- `started_at TEXT NOT NULL`
- `submitted_at TEXT NULL`
- `completed_at TEXT NULL`
- `updated_at TEXT NOT NULL`

知识测试保存由服务端计算的成绩；`score` 固定为百分制，`max_score=100`，趣味测试的成绩字段必须为空。提交采用状态条件更新和幂等键，防止双击或网络重试重复调用分析模型。`UNIQUE(user_id, create_request_id)` 保证同一次重测请求不创建两个 attempt；同一测试最多存在一个 `draft` 或 `analyzing` attempt。

### 4.4 `test_answers`

- `attempt_id TEXT NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE`
- `question_id TEXT NOT NULL`
- `selected_option_id TEXT NOT NULL`
- `answered_at TEXT NOT NULL`
- `PRIMARY KEY(attempt_id, question_id)`

前端每次选择答案后自动 upsert。最终提交时，服务端在事务中验证题数完整、问题属于当前测试、选项属于对应问题、用户和 attempt 所有权一致。

### 4.5 `test_analysis_runs`

- `id TEXT PRIMARY KEY`
- `attempt_id TEXT NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE`
- `ordinal INTEGER NOT NULL`
- `request_id TEXT NOT NULL`
- `lease_id TEXT NOT NULL UNIQUE`
- `status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'abandoned'))`
- `provider_id TEXT NOT NULL`
- `model TEXT NOT NULL`
- `snapshot_json TEXT NOT NULL`
- `started_at TEXT NOT NULL`
- `finished_at TEXT NULL`
- `error_message TEXT NULL`
- `UNIQUE(attempt_id, ordinal)`
- `UNIQUE(attempt_id, request_id)`

每次首次分析或显式重试都创建一条 run，记录当次实际使用的当前 Test 分析模型快照。修改模型配置后重试会使用新配置，同时保留之前失败调用的真实记录。

### 4.6 `test_creation_requests`

- `user_id TEXT NOT NULL`
- `request_id TEXT NOT NULL`
- `status TEXT NOT NULL CHECK(status IN ('generating', 'completed', 'failed'))`
- `test_id TEXT NULL`
- `lease_id TEXT NULL UNIQUE`
- `generation_started_at TEXT NULL`
- `error_message TEXT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `PRIMARY KEY(user_id, request_id)`

`POST /tests` 在调用模型前先用短事务占用 request id，并写入唯一 lease 与 `generation_started_at`。并发或网络重试遇到未超时的 `generating` 时返回现有任务状态，不再次调用模型；`completed` 返回同一 test；`failed` 可由用户显式重试并用新 lease 重新占用。生成 lease 为 10 分钟，应用启动时以及再次读取/重试该请求时回收超时记录。成功写入必须 CAS 当前 request 仍为 `generating` 且 lease 匹配，并在同一个短事务中创建 session、首个 attempt、把 creation request 转为 `completed`；CAS 失败时丢弃迟到结果，不能创建第二个测试。该记录不是测试会话，失败时不会生成半成品 session。

repository 的 generation/analysis reservation 均返回显式状态对象：`state = acquired | in_progress | completed | failed`、`acquired: bool`、可空 `lease_id`，以及已存在的 `test_id` 或 attempt 摘要。只有 `acquired=true` 的调用方可以调用模型；`in_progress` 只能返回/轮询，`completed` 复用既有结果，`failed` 只有显式 retry 标志或 retry endpoint 才能获得新 lease。

### 4.7 索引

- `test_sessions(user_id, updated_at DESC)`
- `test_sessions(user_id, mode, updated_at DESC)`
- `test_attempts(test_id, started_at DESC)`
- `test_attempts(user_id, updated_at DESC)`
- `UNIQUE test_attempts(test_id) WHERE status IN ('draft', 'analyzing')`

## 5. 结构化题目协议

### 5.1 生成请求

出题服务向模型发送：

- 模式：`knowledge` 或 `fun`
- 主题
- 可选额外要求
- 题量
- 知识测试难度
- 精确 JSON 字段定义、数量限制、文本长度限制与禁止项

主题和额外要求按“不可信数据”放入明确分隔的数据块，不得让其覆盖系统约束。

### 5.2 服务端完整题目

共同字段：

```json
{
  "title": "测试标题",
  "description": "测试说明",
  "questions": [
    {
      "id": "q1",
      "prompt": "问题文本",
      "options": [
        {"id": "a", "text": "选项 A"}
      ]
    }
  ]
}
```

知识题额外包含：

- `correct_option_id`
- `explanation`
- `knowledge_points: string[]`

趣味题不得包含正确答案、内部分析标签或维度权重。第一版分析模型直接基于完整题面与用户选择给出结果；Pydantic 的 `extra='forbid'` 会拒绝任何未定义选项字段。

严格限制：

- 测试标题：1 至 120 字符。
- 测试说明：0 至 500 字符。
- 每题题干：1 至 500 字符。
- 每题选项：2 至 6 个。
- 选项文本：1 至 240 字符。
- 知识题解析：1 至 1000 字符。
- 每题知识点：1 至 8 个；单个知识点 1 至 80 字符。
- 问题 id 和选项 id：1 至 40 个 ASCII 字母、数字、下划线或短横线。

### 5.3 公开题目裁剪

测试创建响应、session 详情、draft/failed/analyzing attempt 和未提交历史详情只返回：

- 测试标题、说明、模式与题量。
- 问题 id、问题文本。
- 选项 id、选项文本。

session/questionnaire DTO 永远只返回裁剪后的公开题面，绝不直接返回原始 `questionnaire_json`。知识题的正确答案、解析和知识点映射只保留在后端。正确答案和解析只通过“指定的 completed attempt 结果 DTO”返回；failed、draft、analyzing attempt 均不返回。第一版趣味题不存在内部权重字段。

## 6. OpenAI-compatible 兼容策略

当前供应商配置没有结构化输出能力元数据，因此第一版采用：

1. 非流式、无 tools 的普通 `chat.completions`。
2. 强约束纯 JSON 提示词。
3. 容忍 Markdown code fence 和 JSON 前后少量说明，但只提取一个顶层对象。
4. 使用 Pydantic 严格校验，`extra='forbid'`。
5. 校验问题/选项 id 唯一、题量准确、选项数和文本长度受限、知识答案确实指向本题选项。
6. 首次解析或校验失败时，最多调用一次“只修复为目标 schema”的模型请求；旧输出和 validation errors 都必须作为不可信数据放入边界标记中，不能成为新指令。
7. 第二次仍失败则返回明确的上游格式错误，不创建半成品测试。

出题与分析两类响应都执行相同的“解析、严格校验、最多一次修复”流程。请求的 `max_tokens` 上限为 16,000；本地拒绝超过 256 KiB 的模型文本响应，避免无界解析。

未来只有在 provider profile 明确保存并验证 `json_schema` 或 `json_object` 能力后，才启用原生 `response_format`，不能根据模型名称猜测。

## 7. 计分与分析

### 7.1 知识测试

服务端根据不可变答案键计算：

- `correct_count`
- `question_count`
- `score`（百分制）
- 各知识点正确率

这些数值是唯一可信结果。分析模型接收完整题目、用户选择、正确性、解析、知识点聚合和服务端成绩，只返回：

- 总体评价
- 已掌握内容
- 薄弱知识点
- 针对性建议
- 可选受控图表

模型返回的任何成绩字段均忽略或由 schema 禁止。

知识分析结果的完整 schema 为：

```json
{
  "title": "掌握情况标题",
  "summary": "总体评价",
  "mastered": [{"heading": "已掌握", "body": "具体说明"}],
  "weaknesses": [{"heading": "薄弱点", "body": "具体说明"}],
  "recommendations": [{"heading": "建议", "body": "具体建议"}],
  "charts": []
}
```

Pydantic 使用 `extra='forbid'`。`title` 1 至 120 字符，`summary` 1 至 800 字符；三类 section 各 0 至 6 项且总数至少 1，`heading` 1 至 80 字符，`body` 1 至 1200 字符；`charts` 0 至 2 张。结果 schema 不接受 `score`、`correct_count` 或 `max_score`。

### 7.2 趣味测试

分析模型一次性接收完整题目和全部用户选择，返回：

- 结论标题
- 简短结论
- 详细说明分节
- 最多两张图表

图表只允许：

- `radar`
- `bar`
- `donut`

统一图表数据协议：

```json
{
  "kind": "radar",
  "title": "特质维度",
  "items": [
    {"label": "好奇心", "value": 82, "max_value": 100}
  ]
}
```

约束：图表最多 2 张；单图维度 2 至 8；`value` 和 `max_value` 为有限数字且 `0 <= value <= max_value <= 100`；图表 title 为 1 至 120 字符，label 为 1 至 80 字符，均为纯文本。

趣味分析结果的完整 schema 为：

```json
{
  "title": "结果标题",
  "summary": "简短结论",
  "sections": [{"heading": "特质说明", "body": "具体说明"}],
  "charts": []
}
```

Pydantic 使用 `extra='forbid'`。`title` 1 至 120 字符，`summary` 1 至 800 字符，`sections` 1 至 6 项，section 长度限制与知识结果相同，`charts` 0 至 2 张。两类分析响应首次校验失败都只允许一次修复调用；仍失败时 attempt 进入 `failed`。

## 8. API 设计

### 配置

- `GET /tests/preferences?user_id=...`
- `PUT /tests/preferences?user_id=...`

### 测试会话

- `POST /tests`：请求体必须带客户端 UUID `request_id` 和默认 `false` 的 `retry_failed`。新获得 lease 时等待生成并返回 201；相同 request 正在执行时返回 202 generation status；已完成时返回 200 同一 test；已失败时返回 409，只有用户显式以 `retry_failed=true` 重试才重新获得 lease。
- `GET /tests/creation-requests/{request_id}?user_id=...`：读取 generation 状态；读取前回收该请求的过期 lease。返回 `generating | completed | failed`、可空 test id、安全错误和建议轮询间隔。
- `GET /tests?user_id=...&mode=...&cursor=...&limit=...`：历史列表，按 `(updated_at DESC, id DESC)` 排序并以二者组成稳定游标。
- `GET /tests/{test_id}?user_id=...`：测试详情和 attempt 摘要。
- `DELETE /tests/{test_id}?user_id=...`：删除测试及其 attempts/answers。
- `POST /tests/{test_id}/attempts`：请求体必须带客户端 UUID `request_id`。若同一测试已有 draft/analyzing attempt，直接返回该活动 attempt；否则幂等地复用原题创建新的 draft attempt。

### 作答

- `GET /test-attempts/{attempt_id}?user_id=...`
- `PATCH /test-attempts/{attempt_id}/answers`：自动保存单题或答案快照，不触发模型，仅允许 draft。
- `POST /test-attempts/{attempt_id}/submit`：请求体携带客户端 UUID `request_id` 和前端当前完整答案快照。新获得分析 lease 时执行；相同 request 正在执行时返回 202；已完成或已失败时返回 200 既有 attempt，不重复调用模型。
- `POST /test-attempts/{attempt_id}/retry-analysis`：请求体为 `user_id + request_id`，仅对 failed attempt创建幂等 analysis run。相同 retry request 正在执行时返回 202，已完成时返回 200 既有结果。

资源查询始终同时校验 `user_id`。未知资源和跨用户资源统一返回 404。

未配置 Test 模型、供应商已删除或所选模型为空属于可修复配置冲突，统一返回 409；上游拒绝/不可用或两次结构化输出均失败返回 502。

## 9. 状态与失败恢复

### 9.1 新建测试

`生成请求 -> 模型响应 -> 本地解析校验 -> 必要时一次修复 -> 原子创建 session + draft attempt`

任一步失败均不落半成品 session。

### 9.2 提交测试

`draft -> analyzing -> completed | failed`

- submit 在一个短 SQLite 事务内完成：校验 request id 幂等；CAS `draft -> analyzing`；upsert 请求体中的最终完整答案快照；校验完整性/归属；计算知识成绩；解析当前分析模型；创建 `test_analysis_runs`；写入分析快照、lease 和 `analysis_started_at`。事务提交后才调用模型。
- LLM 调用期间绝不持有 SQLite 写事务。
- 延迟到达的 autosave 因 attempt 已非 draft 而返回 409，不能覆盖最终答卷。
- 知识测试在模型调用前完成并持久化确定性成绩。
- 分析失败保留答案、知识成绩、模型快照和错误信息。
- 用户可显式重试分析；重试使用当时当前的 Test 分析模型并新增 analysis run，不覆盖旧的 completed attempt，也不新建第二条 attempt。
- 分析 lease 为 10 分钟。应用启动时以及读取/retry attempt 时，把超过 10 分钟仍为 `analyzing` 的 attempt CAS 为 `failed`，对应 run 标记 `abandoned`，从而允许恢复。
- 模型返回后的成功或失败写入必须同时 CAS `attempt.status='analyzing' AND attempt.analysis_lease_id=<本次 lease>`，并把同 lease 的 run 从 `running` 条件更新为最终状态；CAS 失败表示旧调用已经超时或被新 run 取代，迟到结果必须丢弃，不能覆盖新结果。
- 活跃 analyzing attempt 对应的测试禁止删除并返回 409；超时回收后可以删除。

所有持久化并返回前端的 `error_message` 都是归一化安全文本，不保存模型原始完整输出、validation payload、API key 或上游响应体。

`get_attempt` 在返回前、`retry_analysis` 在判断状态前、generation status 和重复 `POST /tests` 在 reservation 前都会执行对应资源的 stale recovery；因此服务无需重启也能从过期 `generating/analyzing` 恢复。

## 10. 前端信息架构

### 10.1 产品入口

- 新路由 `/test`，使用现有登录守卫。
- `AppModeSwitcher` 扩展为 Studio / Live / Test 三项。
- Test 页面不显示 Studio 助手、能力、记忆或 Live 音频设置。

### 10.2 页面布局

视觉方向为“编辑部测评实验室”：深色仪器侧栏配暖纸色主画布，以钴蓝和酸性珊瑚色区分知识/趣味模式；使用大号题号、细密刻度、页码与印刷式结果排版形成记忆点。避免通用渐变卡片、聊天气泡和整页圆角容器。动效集中在生成入场、题目翻页和结果展开，遵守 `prefers-reduced-motion`。

延续现有应用的侧栏语言，但为测试工作流单独设计：

- 左侧：新测试按钮、模式筛选、历史测试列表、attempt 次数和最近结果摘要。
- 主区：新建表单、答题流程或结果报告。
- 顶部：Test 标识、出题/分析模型设置入口、产品模式切换。

### 10.3 新建状态

- 知识 / 趣味模式切换。
- 主题输入（必填）。
- 题量 5/10/15/20，默认 10。
- 知识测试难度选择。
- 额外要求（可留空）。
- 生成按钮与非流式生成加载态。

### 10.4 答题状态

- 一次展示一题。
- 顶部或侧边显示进度与已答题状态。
- 上一题 / 下一题；允许修改答案。
- 选择答案后后台自动保存，不打断交互。
- 自动保存失败显示非阻塞状态和重试入口；刷新页面后恢复服务端 draft 答案。
- 未答完时禁用最终提交，并显示剩余题数。
- 提交后进入分析加载态，避免重复点击。
- 刷新后若 attempt 仍在 analyzing，页面轮询 attempt 状态；超时回收为 failed 后显示错误和“重试分析”。

### 10.5 结果状态

知识测试：

- 成绩、正确数、题量。
- 逐题对错与解析。
- 掌握情况、薄弱点、学习建议。
- 知识点正确率图表。

趣味测试：

- 结论卡。
- 详细说明。
- 0 至 2 张受控图表。

共同能力：

- attempt 切换。
- 至少支持选择两个 completed attempts 进入比较视图：知识测试比较成绩、题目对错变化和知识点正确率；趣味测试并列结论，并对共同图表维度做并排比较，无法对齐的维度单独列出。
- 重新测试（同题新 attempt）。
- 新测试（新 session、新题）。
- 删除历史测试。

attempt 创建、自动保存、提交、分析完成/失败和重试都会更新 `test_sessions.updated_at`，历史列表按最近活动排序。

## 11. 图表渲染

第一版不引入大型图表依赖，使用 Vue 组件和本地 SVG/CSS 渲染 `radar`、`bar`、`donut`。模型只返回受控数据，前端决定颜色、坐标、动画和无障碍文本。

任何未知图表类型、数据长度不匹配、非有限数字或越界数值都在后端拒绝，不进入前端渲染。

## 12. 验收标准

- Test 可从顶部产品切换进入，且与 Studio / Live 状态隔离。
- 首次进入可继承 Studio 模型，此后出题与分析模型独立持久化。
- 可生成 5/10/15/20 道单选知识题和趣味题。
- 额外要求留空时可正常生成。
- 知识题在提交前不会通过 API 或前端状态暴露答案。
- 用户可逐题作答、前后切换，选择自动保存，最终一次提交。
- 知识成绩由后端稳定计算，模型无法修改。
- 趣味结果能展示结论、详细说明和受控图表。
- 历史测试可打开；同一测试可保留并切换多次 attempt。
- 可选择两次 completed attempts 查看比较；failed 分析可查看错误并重试，analyzing 刷新后可恢复轮询。
- 重新测试复用原题；新测试生成新题并创建新 session。
- 生成 JSON 无效时最多修复一次，仍失败则不保存半成品。
- 分析失败保留答卷并可重试，不重复创建历史 attempt。
- 后端、前端单元测试与现有全量回归通过。

## 13. 参考交互

在线性格测试通常采用固定单选问卷、维度分布和结论报告，本模块只借鉴这种信息结构，不复制其题库或视觉：

- A Real Me 16 人格雷达测试：<https://www.arealme.com/16-personality-test-radar-version/cn/>
- APESK 16 型人格测试：<https://www.apesk.com/mbti2/16mbti/>
- shiny-mbti：<https://github.com/Sallyn0225/shiny-mbti/blob/main/README_CN.md>
