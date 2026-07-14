import assert from 'node:assert/strict'
import { replaceTimelineBranch } from '../src/utils/message-branch.ts'

type Message = { id: string }

const activeTimeline: Message[] = [
  { id: 'user-1' },
  { id: 'assistant-1' },
  { id: 'user-2' },
  { id: 'assistant-2' },
]

assert.deepEqual(
  replaceTimelineBranch(activeTimeline, 'assistant-1', [{ id: 'retry-streaming' }]).map(({ id }) => id),
  ['user-1', 'retry-streaming'],
)

assert.deepEqual(
  replaceTimelineBranch(activeTimeline, 'user-2', [{ id: 'edited-user' }, { id: 'edit-streaming' }]).map(({ id }) => id),
  ['user-1', 'assistant-1', 'edited-user', 'edit-streaming'],
)

assert.deepEqual(
  replaceTimelineBranch(activeTimeline, 'missing', [{ id: 'streaming' }]).map(({ id }) => id),
  ['user-1', 'assistant-1', 'user-2', 'assistant-2'],
)
