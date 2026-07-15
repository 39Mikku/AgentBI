# 工具调用详情折叠 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将聊天时间线中的工具完成详情默认折叠，提供可读摘要与手动展开，同时保持搜索结果卡片始终展示。

**Architecture:** 新增无状态工具事件格式化工具和独立 Vue 展示组件。`ChatView` 只把时间线事件传给组件，`TimelineCard` 仍作为相邻的独立事件渲染，从结构上保证卡片不进入折叠容器。

**Tech Stack:** Vue 3 Composition API、TypeScript、原生 `details/summary`、Node.js `assert` 测试、Vite。

## Global Constraints

- `tool_started` 显示单行“工具名 · 执行中”，不创建空展开区。
- `tool_finished` 默认折叠，标题显示工具名、完成状态和可选结果数量。
- JSON 使用两空格缩进；无法解析的内容保留原文。
- `card` 事件保持当前时间线位置并始终完整展示。
- 同时兼容 `message.timeline` 与历史 `message.tool_events`。
- 不增加第三方依赖，不改变服务端事件结构。
- 不执行 `git add` 或 `git commit`，由用户手动提交。

---

### Task 1: 工具事件内容格式化

**Files:**
- Create: `Agent-vue/src/utils/tool-event.ts`
- Create: `Agent-vue/tests/tool-event.test.ts`

**Interfaces:**
- Produces: `formatToolEventContent(content?: string): string`
- Produces: `toolEventResultCount(content?: string): number | null`
- Produces: `toolEventSummary(tool: string | undefined, type: ToolEventType, content?: string): string`
- Produces: `ToolEventType = 'tool_started' | 'tool_finished'`

- [ ] **Step 1: Write the failing utility tests**

```ts
import assert from 'node:assert/strict'
import {
  formatToolEventContent,
  toolEventResultCount,
  toolEventSummary,
} from '../src/utils/tool-event.ts'

const videoResult = JSON.stringify({ videos: [{ bvid: 'BV1xx411c7mD' }, { bvid: 'BV1Q541167Qg' }] })
assert.equal(formatToolEventContent(videoResult), JSON.stringify(JSON.parse(videoResult), null, 2))
assert.equal(toolEventResultCount(videoResult), 2)
assert.equal(toolEventResultCount('plain text'), null)
assert.equal(formatToolEventContent('line one\nline two'), 'line one\nline two')
assert.equal(toolEventSummary('搜索哔哩哔哩视频', 'tool_started'), '搜索哔哩哔哩视频 · 执行中')
assert.equal(
  toolEventSummary('搜索哔哩哔哩视频', 'tool_finished', videoResult),
  '搜索哔哩哔哩视频 · 已完成 · 2 项结果',
)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd Agent-vue && node --experimental-strip-types tests/tool-event.test.ts`

Expected: FAIL because `src/utils/tool-event.ts` does not exist.

- [ ] **Step 3: Implement the formatting utility**

```ts
export type ToolEventType = 'tool_started' | 'tool_finished'

function parsedJson(content?: string): unknown {
  if (!content?.trim()) return null
  try {
    return JSON.parse(content)
  } catch {
    return null
  }
}

export function formatToolEventContent(content?: string) {
  const parsed = parsedJson(content)
  return parsed === null ? content || '' : JSON.stringify(parsed, null, 2)
}

export function toolEventResultCount(content?: string): number | null {
  const parsed = parsedJson(content)
  if (Array.isArray(parsed)) return parsed.length
  if (!parsed || typeof parsed !== 'object') return null
  for (const value of Object.values(parsed)) {
    if (Array.isArray(value)) return value.length
  }
  return null
}

export function toolEventSummary(tool: string | undefined, type: ToolEventType, content?: string) {
  const parts = [tool || '工具', type === 'tool_started' ? '执行中' : '已完成']
  const count = type === 'tool_finished' ? toolEventResultCount(content) : null
  if (count !== null) parts.push(`${count} 项结果`)
  return parts.join(' · ')
}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd Agent-vue && node --experimental-strip-types tests/tool-event.test.ts`

Expected: exit code 0 with no assertion output.

### Task 2: 折叠组件与时间线接线

**Files:**
- Create: `Agent-vue/src/components/chat/ToolEventDetails.vue`
- Create: `Agent-vue/tests/tool-event-component.test.ts`
- Modify: `Agent-vue/src/views/ChatView.vue:1-20`
- Modify: `Agent-vue/src/views/ChatView.vue:393-430`
- Modify: `Agent-vue/src/views/ChatView.vue:1098-1117`

**Interfaces:**
- Consumes: Task 1 的 `ToolEventType`、`formatToolEventContent`、`toolEventSummary`。
- Produces: `<ToolEventDetails :type :tool :content />`，默认关闭完成态详情。

- [ ] **Step 1: Write failing structural tests**

```ts
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const component = readFileSync(
  new URL('../src/components/chat/ToolEventDetails.vue', import.meta.url),
  'utf8',
)
const chatView = readFileSync(new URL('../src/views/ChatView.vue', import.meta.url), 'utf8')

assert.match(component, /<details/)
assert.doesNotMatch(component, /<details[^>]*\sopen(?:\s|=|>)/)
assert.match(component, /<summary/)
assert.match(component, /<pre/)
assert.match(chatView, /<ToolEventDetails/)
assert.match(chatView, /<TimelineCard\s+v-else-if="event\.type === 'card'"/)
```

- [ ] **Step 2: Run structural tests and verify RED**

Run: `cd Agent-vue && node --experimental-strip-types tests/tool-event-component.test.ts`

Expected: FAIL because `ToolEventDetails.vue` does not exist.

- [ ] **Step 3: Create `ToolEventDetails.vue`**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import {
  formatToolEventContent,
  toolEventSummary,
  type ToolEventType,
} from '@/utils/tool-event'

const props = defineProps<{ type: ToolEventType; tool?: string; content?: string }>()
const summary = computed(() => toolEventSummary(props.tool, props.type, props.content))
const detail = computed(() => formatToolEventContent(props.content))
</script>

<template>
  <div v-if="type === 'tool_started' || !detail" class="tool-event tool-event-running">
    <span class="tool-signal"></span>{{ summary }}
  </div>
  <details v-else class="tool-event tool-event-result">
    <summary><span class="tool-signal"></span><b>{{ summary }}</b><i>查看详情</i></summary>
    <pre>{{ detail }}</pre>
  </details>
</template>
```

Add these scoped styles:

```css
.tool-event {
  margin: 0 0 10px;
  border-left: 2px solid var(--acid);
  background: rgba(0, 0, 0, 0.035);
  color: #4b4b43;
  font: 11px/1.6 'DM Mono', monospace;
}
.tool-event-running {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
}
.tool-event summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  cursor: pointer;
  list-style: none;
}
.tool-event summary::-webkit-details-marker { display: none; }
.tool-event summary b { font-weight: 500; }
.tool-event summary i {
  margin-left: auto;
  color: #8a8880;
  font-size: 9px;
  font-style: normal;
}
.tool-event-result[open] summary i::before { content: '收起'; }
.tool-event-result[open] summary i { font-size: 0; }
.tool-event-result[open] summary i::before { font-size: 9px; }
.tool-signal {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border: 1px solid #242421;
  background: var(--acid);
}
.tool-event pre {
  max-height: 320px;
  overflow: auto;
  margin: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding: 11px 13px 13px 25px;
  color: #5d5a54;
  font: 10px/1.65 'DM Mono', monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

- [ ] **Step 4: Replace both tool-event render branches in `ChatView.vue`**

Import:

```ts
import ToolEventDetails from '@/components/chat/ToolEventDetails.vue'
```

Timeline branch:

```vue
<ToolEventDetails
  v-else-if="event.type === 'tool_started' || event.type === 'tool_finished'"
  :type="event.type"
  :tool="event.tool"
  :content="event.content"
/>
```

Legacy branch:

```vue
<ToolEventDetails
  v-for="(event, index) in message.tool_events"
  :key="index"
  :type="event.type === 'tool_finished' ? 'tool_finished' : 'tool_started'"
  :tool="typeof event.tool === 'string' ? event.tool : undefined"
  :content="typeof event.content === 'string' ? event.content : undefined"
/>
```

Remove only the obsolete `.tool-event` rules from `ChatView`; retain `.reasoning` unchanged. Do not alter the adjacent `TimelineCard` branch.

- [ ] **Step 5: Run component tests and type checking**

Run:

```powershell
cd Agent-vue
node --experimental-strip-types tests/tool-event-component.test.ts
node --experimental-strip-types tests/tool-event.test.ts
npm run type-check
```

Expected: all commands exit 0.

### Task 3: Regression and rendered verification

**Files:**
- Verify only; no source changes expected.

**Interfaces:**
- Consumes: completed component and utility from Tasks 1-2.
- Produces: verified default-collapse interaction without changing cards.

- [ ] **Step 1: Run all focused frontend tests and production build**

Run:

```powershell
cd Agent-vue
node --experimental-strip-types tests/bilibili-player.test.ts
node --experimental-strip-types tests/tool-event.test.ts
node --experimental-strip-types tests/tool-event-component.test.ts
npm run type-check
npm run build-only
```

Expected: Node assertions exit 0, Vue type checking exits 0, and Vite reports a successful build.

- [ ] **Step 2: Validate in Chrome**

Flow: open an existing conversation containing a Bilibili tool result → confirm the tool completion row is collapsed → confirm the Bilibili card below remains visible → expand the row → confirm formatted JSON appears → collapse it again.

Also verify page title/URL, no framework overlay, no relevant console error, and capture one screenshot showing the collapsed row plus visible card.

- [ ] **Step 3: Review the final diff without staging**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; the new/modified files remain unstaged for the user's manual commit.
