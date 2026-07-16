# Emoji Sticker Upload And Compression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an existing-sticker-sheet input to Emoji Press, allow an empty subject, compress oversized images before upload, and make visual text the first-choice AI sticker name.

**Architecture:** Keep one Emoji Press processing pipeline: both generated sheets and uploaded sheets produce a browser-readable image URL, then reuse `cutStickerSheet` and optional AI naming. Put browser image compression in `utils/image-source.ts` so Studio attachments, image source pickers, Emoji references, and uploaded sheets share the same 2 MB threshold and 2560 px dimension policy.

**Tech Stack:** Vue 3, TypeScript, Canvas API, Vitest, FastAPI, Python unittest.

## Global Constraints

- Trigger compression above 2 MiB or when either image dimension exceeds 2560 px.
- Skip animated GIF compression.
- Preserve PNG transparency; otherwise prefer WebP at quality 0.88 and never replace an original with a larger result.
- Existing attachment server limits remain the final safety boundary.
- Do not commit or stage changes; the user handles Git manually.

---

### Task 1: Shared browser image preparation

**Files:**
- Modify: `Agent-vue/src/utils/image-source.ts`
- Modify: `Agent-vue/src/utils/image-source.test.ts`
- Modify: `Agent-vue/src/components/chat/AttachmentComposer.vue`

**Interfaces:**
- Produces: `prepareImageFile(file: File, options?): Promise<File>` and compression metadata through the returned `File` size/type.
- Consumes: existing `blobToDataUrl`, `fileToDataUrl`, and `uploadAsset` flows.

- [ ] **Step 1: Write failing tests** proving files below 2 MiB remain unchanged, oversized raster images use a provided canvas compressor, GIF files are unchanged, and compression never returns a larger file.
- [ ] **Step 2: Run** `npm run test:unit -- src/utils/image-source.test.ts` and confirm the new tests fail because `prepareImageFile` does not exist.
- [ ] **Step 3: Implement** `prepareImageFile`, image decoding, proportional max-dimension resizing, PNG transparency preservation, WebP quality `0.88`, and `fileToDataUrl` reuse of the prepared file.
- [ ] **Step 4: Update Studio attachment selection** to prepare image files before batch validation and `uploadAsset`, while DOCX files pass through unchanged.
- [ ] **Step 5: Run** `npm run test:unit -- src/utils/image-source.test.ts src/utils/chat-attachments.test.ts` and confirm both suites pass.

### Task 2: Existing sticker-sheet input and optional subject

**Files:**
- Modify: `Agent-vue/src/toolbox/emoji-sticker.ts`
- Modify: `Agent-vue/src/toolbox/emoji-sticker.test.ts`
- Modify: `Agent-vue/src/views/EmojiStickerView.vue`

**Interfaces:**
- `buildStickerPrompt({ subject, style, includeText })` accepts an empty `subject` and uses a stable original-character fallback.
- Uploaded sheets are stored through `uploadAsset`, then assign the same `sheetSourceUrl` consumed by `cutStickerSheet` as generated sheets.

- [ ] **Step 1: Write failing tests** proving an empty subject generates a useful fallback prompt and does not emit empty quotation marks.
- [ ] **Step 2: Run** `npm run test:unit -- src/toolbox/emoji-sticker.test.ts` and verify the fallback test fails.
- [ ] **Step 3: Implement** the prompt fallback and change generation eligibility so an empty subject is valid.
- [ ] **Step 4: Add the uploaded-sheet input** to the sheet stage, prepare it through the shared compressor, set the local sheet source, and immediately reuse cut plus optional naming.
- [ ] **Step 5: Keep generated-sheet attachment behavior unchanged** and confirm uploaded sheets also appear in the attachment library as user uploads.

### Task 3: Text-first sticker naming

**Files:**
- Modify: `AgentBI/src/services/toolbox/emoji_naming.py`
- Modify: `AgentBI/tests/test_toolbox_emoji_naming.py`

**Interfaces:**
- The batch and individual vision prompts use the same priority rule: readable on-image text becomes the name; emotion/action inference is only allowed when no readable text exists.

- [ ] **Step 1: Write failing assertions** for the exact text-first instruction in both batch and individual prompts.
- [ ] **Step 2: Run** `venv\python.exe -m unittest AgentBI.tests.test_toolbox_emoji_naming` and verify the assertions fail.
- [ ] **Step 3: Add one shared naming-rule constant** and include it in both prompt paths.
- [ ] **Step 4: Rerun** the naming tests and confirm they pass.

### Task 4: Verification

**Files:**
- Verify only; no committed QA artifacts.

- [ ] **Step 1: Run** `venv\python.exe -m unittest discover -s AgentBI/tests` and require zero failures.
- [ ] **Step 2: Run** `npm run test:unit` and `npm run build` in `Agent-vue` and require zero failures.
- [ ] **Step 3: Use Chrome** on `http://localhost:5173/toolbox/emoji` to verify: empty subject can generate, uploaded sheet enters cutting, the uploaded-sheet control is visually integrated, and no relevant console errors appear.
- [ ] **Step 4: Verify Studio** on `http://localhost:5173/chat` accepts an oversized image after client-side preparation and displays the reduced size before sending.
- [ ] **Step 5: Run** `git diff --check`, report verification evidence, and leave all Git staging/commit actions to the user.
