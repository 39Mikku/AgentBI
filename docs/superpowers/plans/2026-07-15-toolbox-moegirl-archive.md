# Toolbox Moegirl Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Toolbox workbench that fetches a Moegirlpedia page by name, previews disambiguation pages without saving them, and manages regular cleaned Markdown artifacts from a local directory.

**Architecture:** A scraper extracts current MoeSkin template content, a cleaner converts it to Markdown, a filesystem store manages per-user artifacts, and a thin service/API composes them. The Vue page reuses the existing Markdown renderer and Toolbox visual language while keeping persistence outside SQLite.

**Tech Stack:** Python 3.13, FastAPI, httpx, BeautifulSoup4, html2text, Vue 3, TypeScript, marked/DOMPurify, unittest, Vitest.

## Global Constraints

- Accept only a page name; do not expose URL input.
- Do not call an LLM or copy conversation, role-play, TTS, or Gradio code from the reference project.
- Persist under `AgentBI/data/toolbox/moegirl/`; do not add SQLite tables.
- Scope artifacts by a SHA-256-derived user directory.
- Do not persist raw HTML or disambiguation previews.
- Refreshing the same canonical title replaces one artifact rather than creating a version.
- Preserve visible link text while removing link destinations and images.
- Do not stage or commit Git changes; the user commits manually.

---

### Task 1: MoeSkin extraction and Markdown cleaning

**Files:**
- Modify: `AgentBI/requirements.txt`
- Create: `AgentBI/src/services/toolbox/moegirl/__init__.py`
- Create: `AgentBI/src/services/toolbox/moegirl/scraper.py`
- Create: `AgentBI/src/services/toolbox/moegirl/cleaner.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_scraper.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_cleaner.py`

**Interfaces:**
- Produces: `MoegirlPage(title: str, source_url: str, article_html: str, categories: tuple[str, ...])`.
- Produces: `MoegirlScraper.fetch(name: str) -> Awaitable[MoegirlPage]`.
- Produces: `MoegirlScraper.extract(response_html: str, source_url: str) -> MoegirlPage`.
- Produces: `MoegirlMarkdownCleaner.clean(page: MoegirlPage, fetched_at: datetime) -> CleanedMoegirlPage`.
- Produces: `CleanedMoegirlPage(title, source_url, markdown, is_disambiguation)`.
- Produces typed `MoegirlValidationError`, `MoegirlNotFoundError`, `MoegirlUpstreamError`, and `MoegirlContentError`.

- [ ] **Step 1: Add failing scraper tests**

Use compact inline HTML fixtures so tests are deterministic:

```python
MOESKIN_HTML = '''
<title>雷电芽衣 - 萌娘百科</title>
<script>RLCONF={"wgPageName":"雷电芽衣","wgCategories":["崩坏3角色"]};</script>
<template id="MOE_SKIN_TEMPLATE_BODYCONTENT">
  <div id="mw-content-text"><div class="mw-parser-output"><h2>简介</h2><p>正文</p></div></div>
</template>
'''

def test_extracts_article_from_moeskin_template(self):
    page = MoegirlScraper.extract(MOESKIN_HTML, "https://mzh.moegirl.org.cn/example")
    self.assertEqual(page.title, "雷电芽衣")
    self.assertIn("mw-parser-output", page.article_html)
    self.assertEqual(page.categories, ("崩坏3角色",))

def test_falls_back_to_direct_mediawiki_content(self):
    html = '<h1 id="firstHeading">可莉</h1><div id="mw-content-text"><p>正文</p></div>'
    page = MoegirlScraper.extract(html, "https://mzh.moegirl.org.cn/example")
    self.assertEqual(page.title, "可莉")
```

- [ ] **Step 2: Run scraper tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_scraper -v`

Expected: import failure because the scraper package does not exist.

- [ ] **Step 3: Implement the scraper**

Implementation requirements:

```python
@dataclass(frozen=True)
class MoegirlPage:
    title: str
    source_url: str
    article_html: str
    categories: tuple[str, ...]

class MoegirlScraper:
    BASE_URL = "https://mzh.moegirl.org.cn/"

    def __init__(self, client: httpx.AsyncClient | None = None): ...

    async def fetch(self, name: str) -> MoegirlPage:
        normalized = name.strip()
        if not normalized or len(normalized) > 200:
            raise MoegirlValidationError("条目名称不能为空且不能超过 200 个字符")
        url = self.BASE_URL + quote(normalized, safe="")
        # GET with browser-like User-Agent, Accept-Language, redirects, 30-second timeout.
        # Map 404 to MoegirlNotFoundError and transport/non-2xx errors to MoegirlUpstreamError.
        return self.extract(response.text, str(response.url))

    @staticmethod
    def extract(response_html: str, source_url: str) -> MoegirlPage:
        # Parse template#MOE_SKIN_TEMPLATE_BODYCONTENT.decode_contents() as a second soup.
        # Fall back to the original soup.
        # Select #mw-content-text, .mw-parser-output, .mw-body-content, article, then main.
        # Read wgPageName and wgCategories from the RLCONF JSON assignment; fall back to
        # #firstHeading/h1/title for the title and category link text for categories.
        # Raise MoegirlContentError when title or article HTML is absent.
```

Add explicit requirements:

```text
beautifulsoup4>=4.12,<5
html2text>=2025.4.15,<2027
```

- [ ] **Step 4: Run scraper tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_scraper -v`

Expected: all scraper tests pass.

- [ ] **Step 5: Add failing cleaner tests**

```python
def test_regular_page_keeps_article_text_and_removes_noise(self):
    page = MoegirlPage(
        title="雷电芽衣",
        source_url="https://mzh.moegirl.org.cn/example",
        categories=(),
        article_html='''<div><p>页首噪声</p><h2>简介</h2><p><a href="/x">角色正文</a></p>
          <img src="x.png"><h2>查 · 论 · 编</h2><p>模板噪声</p></div>''',
    )
    result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)
    self.assertFalse(result.is_disambiguation)
    self.assertIn("角色正文", result.markdown)
    self.assertNotIn("/x", result.markdown)
    self.assertNotIn("模板噪声", result.markdown)

def test_disambiguation_keeps_candidate_lists(self):
    page = MoegirlPage(
        title="芽衣",
        source_url="https://mzh.moegirl.org.cn/example",
        categories=("消歧义页",),
        article_html='<p>可以指：</p><h2>作品人物</h2><ul><li><a href="/雷电芽衣">雷电芽衣</a></li></ul>',
    )
    result = MoegirlMarkdownCleaner().clean(page, FIXED_TIME)
    self.assertTrue(result.is_disambiguation)
    self.assertIn("雷电芽衣", result.markdown)
```

- [ ] **Step 6: Run cleaner tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_cleaner -v`

Expected: import failure because the cleaner does not exist.

- [ ] **Step 7: Implement the cleaner**

```python
@dataclass(frozen=True)
class CleanedMoegirlPage:
    title: str
    source_url: str
    markdown: str
    is_disambiguation: bool

class MoegirlMarkdownCleaner:
    def clean(self, page: MoegirlPage, fetched_at: datetime) -> CleanedMoegirlPage:
        is_disambiguation = "消歧义页" in page.categories or self._has_disambiguation_notice(page.article_html)
        # Remove scripts/styles/nav/footer/edit sections/references/navigation boxes/images.
        # Convert with HTML2Text(ignore_links=True, ignore_images=True, body_width=0,
        # unicode_snob=True, ignore_tables=False).
        # Normalize whitespace and raw URLs.
        # Apply regular trimming only when is_disambiguation is false.
        # Wrap with title, source URL, and ISO fetched_at attribution.
```

- [ ] **Step 8: Run all Task 1 tests**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_scraper AgentBI.tests.test_toolbox_moegirl_cleaner -v`

Expected: all scraper and cleaner tests pass.

---

### Task 2: Filesystem artifact repository and archive service

**Files:**
- Create: `AgentBI/src/services/toolbox/moegirl/artifact_store.py`
- Create: `AgentBI/src/services/toolbox/moegirl/service.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_artifact_store.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_service.py`

**Interfaces:**
- Consumes: `MoegirlScraper.fetch`, `MoegirlMarkdownCleaner.clean`, `CleanedMoegirlPage`.
- Produces: `MoegirlArtifactStore.list(user_id)`, `get(user_id, artifact_id)`, `save(user_id, requested_name, cleaned)`, and `delete(user_id, artifact_id)`.
- Produces: `MoegirlArchiveService.fetch(user_id, name) -> Awaitable[MoegirlFetchResult]`.
- Produces: `MoegirlFetchResult(kind, title, source_url, markdown, message, artifact)`.

- [ ] **Step 1: Write failing store tests**

```python
def test_save_upserts_one_artifact_per_user_and_canonical_title(self):
    first = store.save("alice", "芽衣", cleaned_page("雷电芽衣", "first"))
    second = store.save("alice", "雷电芽衣", cleaned_page("雷电芽衣", "second"))
    self.assertEqual(first.id, second.id)
    self.assertEqual(len(store.list("alice")), 1)
    self.assertEqual(store.get("alice", first.id).markdown, "second")

def test_users_are_isolated(self):
    artifact = store.save("alice", "可莉", cleaned_page("可莉", "content"))
    self.assertIsNone(store.get("bob", artifact.id))

def test_delete_removes_only_the_selected_artifact(self): ...
```

- [ ] **Step 2: Run store tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_artifact_store -v`

Expected: import failure because the store does not exist.

- [ ] **Step 3: Implement atomic filesystem storage**

Use dataclasses `MoegirlArtifactSummary` and `MoegirlArtifactDocument`. The constructor accepts `root: Path`, defaulting to `Path(__file__).parents[4] / "data" / "toolbox" / "moegirl"`. Derive user and artifact directories with SHA-256 hex prefixes. Write `content.md.tmp` and `metadata.json.tmp`, then replace their targets only after both temporary writes succeed. Validate artifact IDs with `^[a-f0-9]{24}$`, resolve paths, and verify they stay below the user root.

- [ ] **Step 4: Run store tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_artifact_store -v`

Expected: all artifact-store tests pass.

- [ ] **Step 5: Write failing service tests**

```python
async def test_regular_page_is_saved(self):
    result = await service.fetch("alice", "雷电芽衣")
    self.assertEqual(result.kind, "saved")
    self.assertIsNotNone(result.artifact)
    store.save.assert_called_once()

async def test_disambiguation_is_previewed_without_persistence(self):
    result = await service.fetch("alice", "芽衣")
    self.assertEqual(result.kind, "disambiguation")
    self.assertIsNone(result.artifact)
    store.save.assert_not_called()
```

- [ ] **Step 6: Run service tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_service -v`

Expected: import failure because the archive service does not exist.

- [ ] **Step 7: Implement service orchestration**

The service calls scraper, then cleaner with an injectable clock. It returns `kind="disambiguation"`, `message="该名称指向消歧义页，预览不会保存"`, and no artifact for disambiguation. Otherwise it saves and returns `kind="saved"`, `message="抓取完成并已保存"`, and the artifact summary.

- [ ] **Step 8: Run all Task 2 tests**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_artifact_store AgentBI.tests.test_toolbox_moegirl_service -v`

Expected: all store and service tests pass.

---

### Task 3: FastAPI contract and routes

**Files:**
- Create: `AgentBI/src/schemas/toolbox_moegirl_schema.py`
- Create: `AgentBI/src/api/toolbox_moegirl.py`
- Modify: `AgentBI/main.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_contract.py`
- Create: `AgentBI/tests/test_toolbox_moegirl_api.py`

**Interfaces:**
- Consumes: `MoegirlArchiveService` and `MoegirlArtifactStore`.
- Produces: `POST /toolbox/moegirl/fetch`.
- Produces: `GET /toolbox/moegirl/artifacts`.
- Produces: `GET /toolbox/moegirl/artifacts/{artifact_id}`.
- Produces: `GET /toolbox/moegirl/artifacts/{artifact_id}/download`.
- Produces: `DELETE /toolbox/moegirl/artifacts/{artifact_id}`.

- [ ] **Step 1: Write failing schema and API tests**

```python
def test_fetch_request_trims_identity_and_name(self):
    payload = MoegirlFetchRequest(user_id=" alice ", name=" 雷电芽衣 ")
    self.assertEqual(payload.user_id, "alice")
    self.assertEqual(payload.name, "雷电芽衣")

def test_disambiguation_response_has_no_artifact(self):
    response = client.post("/toolbox/moegirl/fetch", json={"user_id": "alice", "name": "芽衣"})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["kind"], "disambiguation")
    self.assertIsNone(response.json()["artifact"])

def test_download_returns_markdown_attachment(self): ...
def test_delete_returns_204_and_unknown_artifact_returns_404(self): ...
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_contract AgentBI.tests.test_toolbox_moegirl_api -v`

Expected: missing schemas and route failures.

- [ ] **Step 3: Implement schemas and router**

Schemas must use `extra="forbid"`, trim strings, cap `user_id` at 320 and `name` at 200, and expose summary/document/fetch response models. Add `get_moegirl_archive_service(request)` and `get_moegirl_artifact_store(request)` app-state injection points for tests. Map errors exactly:

- `MoegirlValidationError` -> 422
- `MoegirlNotFoundError` -> 404
- `MoegirlUpstreamError` and `MoegirlContentError` -> 502
- unknown artifact -> 404
- artifact write `OSError` -> 500

Download uses `text/markdown; charset=utf-8` and `Content-Disposition` with a safe UTF-8 filename. Register the router in `AgentBI/main.py`.

- [ ] **Step 4: Run focused API tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_moegirl_contract AgentBI.tests.test_toolbox_moegirl_api -v`

Expected: all Moegirl API tests pass.

- [ ] **Step 5: Run the full backend suite**

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`

Expected: all backend tests pass.

---

### Task 4: Toolbox card and Moegirl Archive frontend

**Files:**
- Create: `Agent-vue/src/api/toolbox-moegirl-types.ts`
- Create: `Agent-vue/src/api/toolbox-moegirl.ts`
- Create: `Agent-vue/src/toolbox/moegirl-archive.ts`
- Create: `Agent-vue/src/toolbox/moegirl-archive.test.ts`
- Create: `Agent-vue/src/views/MoegirlArchiveView.vue`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/ToolboxView.vue`

**Interfaces:**
- Produces: typed fetch/list/get/download/delete API functions.
- Produces: `applyFetchResult(history, result)`, `removeArtifact(history, selectedId, deletedId)`, and `selectFallbackArtifact(history)` pure state helpers.
- Consumes: existing `renderMarkdown` from `Agent-vue/src/utils/markdown.ts`.

- [ ] **Step 1: Write failing frontend state tests**

```typescript
it('does not insert a disambiguation preview into saved history', () => {
  const history = [savedArtifact('a')]
  const result = disambiguationResult('芽衣')
  expect(applyFetchResult(history, result)).toEqual(history)
})

it('upserts a saved artifact at the front', () => {
  const next = applyFetchResult([savedArtifact('a')], savedResult('b'))
  expect(next.map((item) => item.id)).toEqual(['b', 'a'])
})

it('selects the next artifact after deleting the current one', () => { ... })
```

- [ ] **Step 2: Run frontend helper tests and verify RED**

Run: `npm run test:unit -- src/toolbox/moegirl-archive.test.ts`

Working directory: `Agent-vue`

Expected: import failure because the helper does not exist.

- [ ] **Step 3: Implement frontend types, API client, and helpers**

Use `/api/toolbox/moegirl` as the client base. `downloadMoegirlArtifact` must return a Blob and derive the filename from `Content-Disposition` when available. Helpers must preserve history on disambiguation, de-duplicate saved results by ID, and return a deterministic next selection after deletion.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run: `npm run test:unit -- src/toolbox/moegirl-archive.test.ts`

Working directory: `Agent-vue`

Expected: all Moegirl frontend helper tests pass.

- [ ] **Step 5: Implement the page and Toolbox entry**

Add route `/toolbox/moegirl`. Build `MoegirlArchiveView.vue` as a responsive two-column workbench:

- page-name form and fetch progress;
- saved-history list with loading and empty states;
- preview header with saved/disambiguation badge;
- sanitized `v-html="renderMarkdown(preview.markdown)"` content;
- refresh, Blob download, and delete actions;
- regular fetch selects and upserts the saved artifact;
- disambiguation replaces only the temporary preview;
- failures preserve the current preview and history.

Update Toolbox copy to `LOCAL UTILITIES · 004`, add a `04 / KNOWLEDGE` card named `MOE ARCHIVE`, and mark manifest item 04 as `READY`.

- [ ] **Step 6: Run full frontend verification**

Run: `npm run test:unit`

Run: `npm run build`

Working directory: `Agent-vue`

Expected: all frontend tests pass and the production build succeeds.

---

### Task 5: Integration and visual verification

**Files:**
- Verify all files from Tasks 1-4.

**Interfaces:**
- Consumes the completed backend and frontend feature.
- Produces a verified unstaged working tree ready for the user's manual commit.

- [ ] **Step 1: Run fresh complete verification**

Run from repository root:

```powershell
.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"
Push-Location Agent-vue
npm run test:unit
npm run build
Pop-Location
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 2: Run a single live scraper smoke check**

Use the backend service directly with `芽衣` and a temporary artifact root. Verify `kind == "disambiguation"`, the Markdown contains `雷电芽衣`, and the artifact root remains empty. Do not save the smoke result into production history.

- [ ] **Step 3: Verify through Chrome**

Using the required Chrome plugin:

- open `/toolbox` and verify the fourth card;
- open `/toolbox/moegirl`;
- verify the initial empty state, disabled/active fetch button states, history rail, and Markdown layout;
- perform at most one live `芽衣` fetch;
- verify the disambiguation warning and preview;
- verify no history item is created;
- verify desktop and narrow layouts have no horizontal overflow.

- [ ] **Step 4: Inspect final workspace state**

Run: `git status --short` and `git diff --stat`.

Expected: only intended source, tests, requirements, specs, and plans are modified or untracked; nothing is staged or committed.
