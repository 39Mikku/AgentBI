import { describe, expect, it, vi } from 'vitest'

import { LiveSocketClient } from './LiveSocketClient'

class FakeSocket {
  static readonly OPEN = 1
  readyState = FakeSocket.OPEN
  binaryType = ''
  sent: Array<string | ArrayBuffer> = []
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent<string | ArrayBuffer | Blob>) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()

  send(payload: string | ArrayBuffer) {
    this.sent.push(payload)
  }
}

describe('LiveSocketClient', () => {
  it('opens the user-scoped socket and sends the session snapshot first', async () => {
    const socket = new FakeSocket()
    const client = new LiveSocketClient({
      baseUrl: 'ws://localhost:5173/api/live/ws',
      createSocket: vi.fn(() => socket),
      onEvent: vi.fn(),
      onAudio: vi.fn(),
    })

    const connecting = client.connect('elysia@example.com', {
      type: 'session.start',
      role_id: 'role-a',
      conversation_id: 'thread-a',
    })
    socket.onopen?.()
    await connecting

    expect(client.url).toBe(
      'ws://localhost:5173/api/live/ws?user_id=elysia%40example.com',
    )
    expect(JSON.parse(String(socket.sent[0]))).toMatchObject({
      type: 'session.start',
      role_id: 'role-a',
      conversation_id: 'thread-a',
    })
  })

  it('keeps binary audio separate from normalized JSON events', async () => {
    const socket = new FakeSocket()
    const onEvent = vi.fn()
    const onAudio = vi.fn()
    const client = new LiveSocketClient({
      baseUrl: 'ws://localhost/api/live/ws',
      createSocket: () => socket,
      onEvent,
      onAudio,
    })
    const connecting = client.connect('user', {
      type: 'session.start',
      role_id: 'role-b',
      conversation_id: 'thread-b',
    })
    socket.onopen?.()
    await connecting

    socket.onmessage?.({ data: '{"type":"session.ready"}' } as MessageEvent<string>)
    const pcm = new Uint8Array([1, 2, 3, 4]).buffer
    socket.onmessage?.({ data: pcm } as MessageEvent<ArrayBuffer>)
    client.sendAudio(pcm)

    expect(onEvent).toHaveBeenCalledWith({ type: 'session.ready' })
    expect(onAudio).toHaveBeenCalledWith(pcm)
    expect(socket.sent.at(-1)).toBe(pcm)
  })

  it('sends a graceful end control before closing', async () => {
    const socket = new FakeSocket()
    const client = new LiveSocketClient({
      baseUrl: 'ws://localhost/api/live/ws',
      createSocket: () => socket,
      onEvent: vi.fn(),
      onAudio: vi.fn(),
    })
    const connecting = client.connect('user', {
      type: 'session.start',
      role_id: 'role-a',
      conversation_id: 'thread-a',
    })
    socket.onopen?.()
    await connecting

    client.close()

    expect(JSON.parse(String(socket.sent.at(-1)))).toEqual({ type: 'session.end' })
    expect(socket.close).toHaveBeenCalledOnce()
  })
})
