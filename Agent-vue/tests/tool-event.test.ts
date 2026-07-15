import assert from 'node:assert/strict'
import {
  formatToolEventContent,
  toolEventResultCount,
  toolEventSummary,
} from '../src/utils/tool-event.ts'

const videoResult = JSON.stringify({
  videos: [{ bvid: 'BV1xx411c7mD' }, { bvid: 'BV1Q541167Qg' }],
})

assert.equal(formatToolEventContent(videoResult), JSON.stringify(JSON.parse(videoResult), null, 2))
assert.equal(toolEventResultCount(videoResult), 2)
assert.equal(toolEventResultCount('plain text'), null)
assert.equal(formatToolEventContent('line one\nline two'), 'line one\nline two')
assert.equal(
  toolEventSummary('搜索哔哩哔哩视频', 'tool_started'),
  '搜索哔哩哔哩视频 · 执行中',
)
assert.equal(
  toolEventSummary('搜索哔哩哔哩视频', 'tool_finished', videoResult),
  '搜索哔哩哔哩视频 · 已完成 · 2 项结果',
)
