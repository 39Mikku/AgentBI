# Toolbox Moegirl Archive Design

## Goal

Add a fourth Toolbox utility that accepts a Moegirlpedia page name, fetches the matching page, cleans its article body into readable Markdown, and manages saved results from a project-local directory.

This utility does not call an LLM, does not reuse the source project's conversation features, and does not store artifact metadata in SQLite.

## Scope

### Included

- Accept one page or character name, such as `雷电芽衣`.
- Build the Moegirlpedia URL internally; users never paste a URL.
- Fetch and extract the current MoeSkin article body.
- Convert the article body to cleaned Markdown.
- Detect disambiguation pages.
- Return a cleaned disambiguation preview without persisting it.
- Persist regular-page Markdown and metadata under `AgentBI/data/toolbox/moegirl/`.
- List, preview, refresh, download, and delete saved artifacts.
- Scope local artifacts by the current `user_id`.
- Add a fourth card and manifest entry to the Toolbox home.

### Excluded

- Any LLM, assistant, character, role-play, prompt, memory, TTS, or conversation behavior from the reference project.
- URL input.
- Crawling multiple linked pages automatically.
- Image downloading or offline image archives.
- SQLite records for this utility.
- Version history for repeated fetches of the same canonical page.
- Editing Markdown inside the application.

## Reference Implementation Findings

The reference implementation in `工具箱/次元通讯终端/character.py` performs these useful steps:

1. Build `https://mzh.moegirl.org.cn/{encoded_name}`.
2. Fetch HTML with a browser-like user agent.
3. Select the MediaWiki article body.
4. Remove site chrome, scripts, edit controls, references, navigation boxes, images, and link destinations.
5. Convert HTML to Markdown.
6. Prefer content beginning at `基本资料`, falling back to an `简介` heading.
7. Remove selected noisy sections and stop at `查 · 论 · 编`.
8. Add title and source attribution.

The current MoeSkin response wraps the actual server-rendered article inside `template#MOE_SKIN_TEMPLATE_BODYCONTENT`. The new scraper must parse that template content first, with the older direct MediaWiki selectors as fallbacks.

## Architecture

The implementation is split into three independent backend units:

### `MoegirlScraper`

- Validates and normalizes the requested name.
- URL-encodes the name and performs the HTTP request with `httpx`.
- Follows redirects and records the final canonical source URL.
- Extracts the article title, article HTML, and page categories.
- Classifies the result as a regular page or disambiguation page.
- Raises typed errors for invalid input, unavailable pages, timeouts, non-success responses, or missing article content.

### `MoegirlMarkdownCleaner`

- Accepts extracted article HTML rather than making network requests.
- Removes non-article elements.
- Converts HTML using `html2text`.
- Preserves headings, lists, tables, emphasis, and visible link text.
- Removes image references, link destinations, raw external URLs, edit controls, references, navigation templates, and excessive whitespace.
- Uses the original regular-page trimming rules around `基本资料`, `简介`, noisy sections, and `查 · 论 · 编`.
- Uses a separate disambiguation mode that keeps the introductory sentence, section headings, and candidate lists. It does not apply the regular-page `基本资料` trimming.
- Adds title, source URL, and fetch timestamp to the final Markdown.

### `MoegirlArtifactStore`

- Persists artifacts only for regular pages.
- Uses the filesystem as both content storage and history index.
- Lists metadata by scanning small `metadata.json` files.
- Reads Markdown only when an artifact is opened or downloaded.
- Uses atomic replacement for Markdown and metadata writes.
- Restricts all resolved paths to the configured Moegirl artifact root.

The API composes these units through a small `MoegirlArchiveService` so HTTP concerns, scraping, cleaning, and persistence remain independently testable.

## Local Storage Layout

```text
AgentBI/data/toolbox/moegirl/
  users/
    <sha256(user_id)-prefix>/
      <artifact_id>/
        content.md
        metadata.json
```

- The user directory is a stable SHA-256 prefix rather than the email itself.
- `artifact_id` is derived from the normalized canonical page title, so fetching the same page again replaces its prior artifact instead of creating duplicates.
- `metadata.json` contains:
  - `id`
  - `title`
  - `requested_name`
  - `source_url`
  - `fetched_at`
  - `updated_at`
  - `character_count`
  - `content_sha256`
- The raw HTML response is never stored.
- Disambiguation results never create a directory or file.
- The existing `.gitignore` already excludes `AgentBI/data/`.

## Disambiguation Behavior

Disambiguation is detected from the MediaWiki `消歧义页` category, with the article's semantic disambiguation notice as a fallback.

For a request such as `芽衣`:

1. The backend fetches and cleans the page normally.
2. The response uses `kind: "disambiguation"`.
3. The response contains the page title, source URL, warning message, and temporary Markdown preview.
4. The artifact store is not called.
5. The frontend shows a clear warning that the name is ambiguous and the preview is not saved.
6. The user reads or copies a precise candidate name, replaces the input, and submits again.

The first phase deliberately avoids heuristic one-click candidate extraction because list items also contain work titles and other internal links that are not character candidates.

## API Contract

All endpoints use the existing `/toolbox` namespace.

### Fetch

`POST /toolbox/moegirl/fetch`

Request:

```json
{
  "user_id": "user@example.com",
  "name": "雷电芽衣"
}
```

Response:

```json
{
  "kind": "saved",
  "title": "雷电芽衣",
  "source_url": "https://mzh.moegirl.org.cn/...",
  "markdown": "# 雷电芽衣\n...",
  "message": "抓取完成并已保存",
  "artifact": {
    "id": "...",
    "title": "雷电芽衣",
    "source_url": "https://mzh.moegirl.org.cn/...",
    "fetched_at": "2026-07-15T23:00:00+08:00",
    "updated_at": "2026-07-15T23:00:00+08:00",
    "character_count": 12345
  }
}
```

For disambiguation, `kind` is `disambiguation` and `artifact` is `null`.

### Artifact Management

- `GET /toolbox/moegirl/artifacts?user_id=...` lists saved metadata, newest first.
- `GET /toolbox/moegirl/artifacts/{artifact_id}?user_id=...` returns metadata and Markdown.
- `GET /toolbox/moegirl/artifacts/{artifact_id}/download?user_id=...` downloads the Markdown file.
- `DELETE /toolbox/moegirl/artifacts/{artifact_id}?user_id=...` removes its local directory.

Fetching an existing canonical title is also the refresh operation.

## Frontend

### Toolbox Home

- Change the utility count from `003` to `004`.
- Add a fourth `MOE ARCHIVE` tool card.
- Mark manifest item `04` as ready.
- Preserve the existing industrial editorial Toolbox visual language.

### Moegirl Archive Page

The page uses a two-column workbench:

- Left rail:
  - page-name input;
  - fetch button and progress state;
  - concise network or validation error;
  - saved artifact list;
  - selected state, updated time, character count;
  - refresh, download, and delete actions.
- Right workspace:
  - selected title and source attribution;
  - saved/disambiguation state badge;
  - rendered Markdown preview;
  - empty state before the first fetch.

On successful regular fetch, the new artifact becomes selected and the saved list refreshes. On disambiguation, the temporary preview replaces the current preview but does not appear in history. Deleting the selected artifact clears the preview or selects the next artifact.

## Error Handling

- Blank or overlong names return HTTP 422.
- A page that resolves to a missing article returns HTTP 404.
- Network timeout or upstream unavailability returns HTTP 502.
- A successful response without extractable article content returns HTTP 502.
- Filesystem write failures return HTTP 500 without deleting an existing valid artifact.
- Unknown or cross-user artifact IDs return HTTP 404.
- Failed requests never replace the current frontend preview or mutate saved artifacts.

No raw upstream HTML or local absolute storage path is exposed to the frontend.

## Dependencies

Add explicit backend requirements for:

- `beautifulsoup4`
- `html2text`

Continue using the existing `httpx` dependency. Do not add Gradio, requests, or any dependency from the reference project that is unrelated to scraping and conversion.

## Testing

### Backend Unit Tests

- Extract article content from the current MoeSkin template wrapper.
- Fall back to direct MediaWiki content selectors.
- Convert a regular fixture into expected cleaned Markdown.
- Detect a disambiguation fixture and preserve its candidate lists.
- Verify disambiguation never calls the artifact store.
- Upsert the same canonical page into one artifact directory.
- Isolate users and reject path traversal.
- Preserve an existing artifact if a refresh write fails.

### API Tests

- Saved fetch response and artifact CRUD.
- Disambiguation response with no persisted artifact.
- Validation, missing-page, upstream, and not-found mappings.
- Markdown download headers and filename.

### Frontend Tests

- Fetch response state transition.
- Disambiguation preview is not inserted into history.
- Selecting and deleting artifacts updates the preview predictably.

### Final Verification

- Full backend test suite.
- Full frontend unit tests and production build.
- `git diff --check`.
- Chrome visual and interaction inspection at desktop and narrow widths without issuing unnecessary repeated live requests.

## Acceptance Criteria

- A user can enter an exact Moegirlpedia page name and receive cleaned Markdown.
- Regular results survive application restarts through the local artifact directory.
- History can be listed, opened, refreshed, downloaded, and deleted.
- `芽衣` produces a readable disambiguation preview and no persisted artifact.
- The feature does not call an LLM or write to SQLite.
- The source project's chat, TTS, and role-play code is not copied into AgentBI.
