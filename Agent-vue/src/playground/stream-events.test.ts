import { describe, expect, it } from 'vitest'

import type { PlaygroundMessage } from '@/api/playground-types'
import { applyPlaygroundStreamEvent } from './stream-events'


function makeStreamingMessage(): PlaygroundMessage {
  return {
    id: 'temporary',
    conversation_id: 'conversation',
    user_id: 'user',
    role: 'assistant',
    content: '',
    tool_events: [],
    timeline: [],
    status: 'streaming',
    metadata: {},
  }
}


describe('playground stream event reducer', () => {
  it('stores state and options outside visible message content', () => {
    const message = makeStreamingMessage()

    applyPlaygroundStreamEvent(message, { event: 'delta', data: { content: '正文' } })
    applyPlaygroundStreamEvent(message, {
      event: 'state_snapshot',
      data: { snapshot: { affection: 4 } },
    })
    applyPlaygroundStreamEvent(message, {
      event: 'action_options',
      data: { options: [{ text: '继续' }] },
    })

    expect(message.content).toBe('正文')
    expect(message.metadata.state_snapshot).toEqual({ affection: 4 })
    expect(message.metadata.action_options).toEqual([{ text: '继续' }])
  })

  it('accumulates reasoning and finalizes status', () => {
    const message = makeStreamingMessage()
    applyPlaygroundStreamEvent(message, {
      event: 'reasoning_summary',
      data: { content: '第一段' },
    })
    applyPlaygroundStreamEvent(message, {
      event: 'reasoning_summary',
      data: { content: '第二段' },
    })
    applyPlaygroundStreamEvent(message, { event: 'done', data: {} })

    expect(message.reasoning_summary).toBe('第一段第二段')
    expect(message.status).toBe('complete')
  })
})
