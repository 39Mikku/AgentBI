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
