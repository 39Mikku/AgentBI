import { describe, expect, it } from 'vitest'

import { applyLiveEvent, createLiveState } from './live-state'

describe('Live state reducer', () => {
  it('merges user transcript updates by item id and replaces stash on final text', () => {
    const state = createLiveState()

    applyLiveEvent(state, {
      type: 'user.transcript.delta',
      item_id: 'user-1',
      text: '你好',
      stash: '世界',
    })
    applyLiveEvent(state, {
      type: 'user.transcript.delta',
      item_id: 'user-1',
      text: '你好世',
      stash: '界',
    })
    applyLiveEvent(state, {
      type: 'user.transcript.final',
      item_id: 'user-1',
      transcript: '你好世界',
    })

    expect(state.transcripts).toHaveLength(1)
    expect(state.transcripts[0]).toMatchObject({
      id: 'user-1',
      role: 'user',
      text: '你好世界',
      stash: '',
      final: true,
    })
  })

  it('appends assistant subtitle deltas and finalizes the same row', () => {
    const state = createLiveState()

    applyLiveEvent(state, {
      type: 'assistant.transcript.delta',
      item_id: 'assistant-1',
      delta: '你',
    })
    applyLiveEvent(state, {
      type: 'assistant.transcript.delta',
      item_id: 'assistant-1',
      delta: '好',
    })
    applyLiveEvent(state, {
      type: 'assistant.transcript.final',
      item_id: 'assistant-1',
      transcript: '你好',
    })

    expect(state.transcripts).toEqual([
      {
        id: 'assistant-1',
        role: 'assistant',
        text: '你好',
        stash: '',
        final: true,
        interrupted: false,
      },
    ])
  })

  it('requests immediate playback clearing when the user interrupts the model', () => {
    const state = createLiveState()
    state.phase = 'speaking'
    applyLiveEvent(state, {
      type: 'assistant.transcript.delta',
      item_id: 'assistant-1',
      delta: '还没说完',
    })

    const speechStarted = applyLiveEvent(state, {
      type: 'state.listening',
      item_id: 'user-1',
    })
    const interrupted = applyLiveEvent(state, { type: 'response.interrupted' })

    expect(speechStarted.clearPlayback).toBe(true)
    expect(interrupted.clearPlayback).toBe(true)
    expect(state.phase).toBe('listening')
    expect(state.transcripts[0]?.interrupted).toBe(true)
  })

  it('maps connection, generation, error, and close events to explicit phases', () => {
    const state = createLiveState()

    applyLiveEvent(state, { type: 'session.ready' })
    expect(state.phase).toBe('listening')
    applyLiveEvent(state, { type: 'state.thinking' })
    expect(state.phase).toBe('thinking')
    applyLiveEvent(state, { type: 'state.speaking' })
    expect(state.phase).toBe('speaking')
    applyLiveEvent(state, {
      type: 'session.error',
      code: 'network',
      message: '连接中断',
      recoverable: true,
    })
    expect(state.phase).toBe('error')
    expect(state.error).toBe('连接中断')
    applyLiveEvent(state, { type: 'session.closed' })
    expect(state.phase).toBe('idle')
  })
})
