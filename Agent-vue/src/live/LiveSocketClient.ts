import type { LiveServerEvent, LiveSessionStart } from '@/api/live-types'

interface SocketLike {
  readyState: number
  binaryType: string
  onopen: (() => void) | null
  onmessage: ((event: MessageEvent<string | ArrayBuffer | Blob>) => void) | null
  onclose: (() => void) | null
  onerror: (() => void) | null
  send(payload: string | ArrayBuffer): void
  close(): void
}

export interface LiveSocketDependencies {
  baseUrl: string
  createSocket(url: string): SocketLike
  onEvent(event: LiveServerEvent): void
  onAudio(pcm: ArrayBuffer): void
  onClose?(): void
  onError?(): void
}

function defaultBaseUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/live/ws`
}

export class LiveSocketClient {
  private readonly dependencies: LiveSocketDependencies
  private socket: SocketLike | null = null
  url = ''

  constructor(dependencies: Partial<LiveSocketDependencies> & Pick<LiveSocketDependencies, 'onEvent' | 'onAudio'>) {
    this.dependencies = {
      baseUrl: dependencies.baseUrl || defaultBaseUrl(),
      createSocket:
        dependencies.createSocket || ((url) => new WebSocket(url) as unknown as SocketLike),
      onEvent: dependencies.onEvent,
      onAudio: dependencies.onAudio,
      onClose: dependencies.onClose,
      onError: dependencies.onError,
    }
  }

  connect(userId: string, start: LiveSessionStart): Promise<void> {
    this.url = `${this.dependencies.baseUrl}?user_id=${encodeURIComponent(userId)}`
    const socket = this.dependencies.createSocket(this.url)
    socket.binaryType = 'arraybuffer'
    this.socket = socket
    return new Promise((resolve, reject) => {
      let opened = false
      socket.onopen = () => {
        opened = true
        socket.send(JSON.stringify(start))
        resolve()
      }
      socket.onmessage = (message) => this.receive(message.data)
      socket.onerror = () => {
        this.dependencies.onError?.()
        if (!opened) reject(new Error('无法建立 Live WebSocket 连接'))
      }
      socket.onclose = () => {
        if (this.socket === socket) this.socket = null
        this.dependencies.onClose?.()
      }
    })
  }

  sendAudio(pcm: ArrayBuffer): void {
    if (this.socket?.readyState === 1) this.socket.send(pcm)
  }

  close(): void {
    const socket = this.socket
    if (!socket) return
    if (socket.readyState === 1) socket.send(JSON.stringify({ type: 'session.end' }))
    socket.close()
    this.socket = null
  }

  private receive(data: string | ArrayBuffer | Blob): void {
    if (typeof data === 'string') {
      try {
        this.dependencies.onEvent(JSON.parse(data) as LiveServerEvent)
      } catch {
        this.dependencies.onError?.()
      }
      return
    }
    if (data instanceof ArrayBuffer) {
      this.dependencies.onAudio(data)
      return
    }
    void data.arrayBuffer().then((buffer) => this.dependencies.onAudio(buffer))
  }
}
