import { describe, expect, it, vi } from 'vitest'

import type { LiveConversation, LiveServerEvent } from '@/api/live-types'
import { createLiveRuntime } from './live'

function runtimeHarness(options: { empty?: boolean } = {}) {
  let onPcm: ((pcm: ArrayBuffer) => void) | null = null
  let callbacks:
    | {
        onEvent(event: LiveServerEvent): void
        onAudio(pcm: ArrayBuffer): void
        onClose(): void
        onError(): void
      }
    | undefined
  const roles = [
    {
      id: 'role-a', user_id: 'alice', name: 'A', instructions: 'A prompt', voice: 'longanqian',
      avatar_data_url: null, memory_enabled: true, is_default: true,
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
    },
    {
      id: 'role-b', user_id: 'alice', name: 'B', instructions: 'B prompt', voice: 'clone-001',
      avatar_data_url: null, memory_enabled: false, is_default: false,
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
    },
  ]
  const conversations = {
    'role-a': options.empty ? [] : [{
      id: 'thread-a', user_id: 'alice', role_id: 'role-a', title: 'A thread',
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
      last_message_at: '2026-07-15T00:00:00Z',
    }],
    'role-b': [{
      id: 'thread-b', user_id: 'alice', role_id: 'role-b', title: 'B thread',
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
      last_message_at: '2026-07-15T00:00:00Z',
    }],
  }
  const socket = {
    connect: vi.fn().mockResolvedValue(undefined),
    sendAudio: vi.fn(),
    close: vi.fn(),
  }
  const microphone = {
    start: vi.fn(async (callback: (pcm: ArrayBuffer) => void) => { onPcm = callback }),
    setMuted: vi.fn(),
    stop: vi.fn().mockResolvedValue(undefined),
  }
  const player = {
    start: vi.fn().mockResolvedValue(undefined),
    enqueue: vi.fn(),
    clear: vi.fn(),
    stop: vi.fn().mockResolvedValue(undefined),
  }
  const dependencies = {
    loadPreferences: vi.fn().mockResolvedValue({
      user_id: 'alice', model: 'qwen-audio-3.0-realtime-flash' as const,
      history_context_turns: 12, max_history_turns: 20,
    }),
    savePreferences: vi.fn(async (_userId, preferences) => ({ user_id: 'alice', ...preferences })),
    listRoles: vi.fn().mockResolvedValue(roles),
    createRole: vi.fn(), updateRole: vi.fn(), deleteRole: vi.fn(),
    getRoleMemory: vi.fn().mockResolvedValue({ user_id: 'alice', role_id: 'role-a', content: '', last_message_id: null, updated_at: null }),
    saveRoleMemory: vi.fn(), clearRoleMemory: vi.fn(), refreshRoleMemory: vi.fn(),
    listConversations: vi.fn(async (_userId: string, roleId: 'role-a' | 'role-b') => conversations[roleId]),
    createConversation: vi.fn(async ({ user_id, role_id }) => ({
      id: 'thread-new', user_id, role_id, title: '新语音会话',
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
      last_message_at: '2026-07-15T00:00:00Z',
    })),
    updateConversation: vi.fn(), deleteConversation: vi.fn(),
    listMessages: vi.fn(async (_userId: string, conversationId: string) => conversationId === 'thread-a' ? [{
      id: 'message-u1', thread_id: 'thread-a', user_id: 'alice', role_id: 'role-a',
      item_id: 'u1', role: 'user' as const, content: '旧文本', status: 'complete' as const,
      created_at: '2026-07-15T00:00:00Z', updated_at: '2026-07-15T00:00:00Z',
    }] : []),
    delay: vi.fn().mockResolvedValue(undefined),
    createSocket: vi.fn((value) => { callbacks = value; return socket }),
    microphone,
    player,
  }
  return {
    dependencies, socket, microphone, player,
    emit: (event: LiveServerEvent) => callbacks?.onEvent(event),
    emitAudio: (pcm: ArrayBuffer) => callbacks?.onAudio(pcm),
    emitMic: (pcm: ArrayBuffer) => onPcm?.(pcm),
  }
}

describe('Live workspace runtime', () => {
  it('loads role-scoped conversations and switches to another role independently', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)

    await live.loadWorkspace('alice')
    expect(live.activeRoleId.value).toBe('role-a')
    expect(live.activeConversationId.value).toBe('thread-a')
    expect(live.state.transcripts[0]!.text).toBe('旧文本')

    await live.selectRole('role-b', 'alice')
    expect(live.activeRoleId.value).toBe('role-b')
    expect(live.activeConversationId.value).toBe('thread-b')
    expect(harness.dependencies.listConversations).toHaveBeenLastCalledWith('alice', 'role-b')
  })

  it('creates an empty conversation before a new call and sends role plus thread ids', async () => {
    const harness = runtimeHarness({ empty: true })
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')

    await live.startCall('alice')

    expect(harness.dependencies.createConversation).toHaveBeenCalledWith({ user_id: 'alice', role_id: 'role-a' })
    expect(harness.socket.connect).toHaveBeenCalledWith('alice', {
      type: 'session.start', role_id: 'role-a', conversation_id: 'thread-new',
    })
  })

  it('continues the selected conversation without creating another one', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')

    await live.startCall('alice')

    expect(harness.dependencies.createConversation).not.toHaveBeenCalled()
    expect(harness.socket.connect).toHaveBeenCalledWith('alice', {
      type: 'session.start', role_id: 'role-a', conversation_id: 'thread-a',
    })
  })

  it('merges final persisted events into loaded history without duplicates', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')

    harness.emit({ type: 'user.transcript.delta', item_id: 'u1', text: '新' })
    harness.emit({
      type: 'user.transcript.final', item_id: 'u1', transcript: '新文本',
      message_id: 'message-u1', conversation_id: 'thread-a', status: 'complete',
    })

    expect(live.state.transcripts).toHaveLength(1)
    expect(live.state.transcripts[0]!.text).toBe('新文本')
    expect(live.state.transcripts[0]!.messageId).toBe('message-u1')
  })

  it('keeps the default title until the server reloads a generated title', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')
    live.currentConversation.value!.title = '新语音会话'

    harness.emit({
      type: 'user.transcript.final', item_id: 'u-title', transcript: '这句话不能直接成为标题',
      message_id: 'message-title', conversation_id: 'thread-a', status: 'complete',
    })

    expect(live.currentConversation.value!.title).toBe('新语音会话')
  })

  it('sends microphone frames only after ready and keeps interruption playback behavior', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')
    await live.startCall('alice')
    const pcm = new Uint8Array([1, 2]).buffer

    harness.emitMic(pcm)
    expect(harness.socket.sendAudio).not.toHaveBeenCalled()
    harness.emit({ type: 'session.ready' })
    harness.emitMic(pcm)
    expect(harness.socket.sendAudio).toHaveBeenCalledWith(pcm)

    live.toggleMute()
    harness.emit({ type: 'response.interrupted' })
    expect(harness.microphone.setMuted).toHaveBeenCalledWith(true)
    expect(harness.player.clear).toHaveBeenCalled()
  })

  it('locks workspace settings while active and releases audio resources on end', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')
    await live.startCall('alice')

    expect(live.canEditSettings.value).toBe(false)
    await live.endCall()
    expect(harness.socket.close).toHaveBeenCalledOnce()
    expect(harness.microphone.stop).toHaveBeenCalledOnce()
    expect(harness.player.stop).toHaveBeenCalledOnce()
    expect(live.state.phase).toBe('idle')
  })

  it('refreshes a default title until the background title model finishes', async () => {
    const harness = runtimeHarness()
    const live = createLiveRuntime(harness.dependencies)
    await live.loadWorkspace('alice')
    live.currentConversation.value!.title = '新语音会话'
    const base = harness.dependencies.listConversations.mock.results[0]!.value
    const initial = await base as LiveConversation[]
    harness.dependencies.listConversations
      .mockResolvedValueOnce(initial.map((item) => ({ ...item, title: '新语音会话' })))
      .mockResolvedValueOnce(initial.map((item) => ({ ...item, title: '旅行计划' })))

    await live.startCall('alice')
    await live.endCall()

    expect(live.currentConversation.value!.title).toBe('旅行计划')
    expect(harness.dependencies.listConversations).toHaveBeenCalledTimes(3)
  })
})
