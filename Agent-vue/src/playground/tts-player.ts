export type PlaygroundTtsStatus = 'idle' | 'loading' | 'playing' | 'error'

interface AudioHandle {
  currentTime: number
  onended: HTMLMediaElement['onended']
  onerror: HTMLMediaElement['onerror']
  pause: () => void
  play: () => Promise<void>
}

interface PlaygroundTtsPlayerDependencies {
  createObjectURL: (blob: Blob) => string
  revokeObjectURL: (url: string) => void
  createAudio: (url: string) => AudioHandle
  onChange?: (messageId: string, status: PlaygroundTtsStatus, error?: string) => void
}

function defaultDependencies(): PlaygroundTtsPlayerDependencies {
  return {
    createObjectURL: (blob) => URL.createObjectURL(blob),
    revokeObjectURL: (url) => URL.revokeObjectURL(url),
    createAudio: (url) => new Audio(url),
  }
}

export class PlaygroundTtsPlayer {
  private readonly dependencies: PlaygroundTtsPlayerDependencies
  private readonly urls = new Map<string, string>()
  private readonly statuses = new Map<string, PlaygroundTtsStatus>()
  private readonly errors = new Map<string, string>()
  private activeAudio: AudioHandle | null = null
  private activeMessageId = ''

  constructor(dependencies: PlaygroundTtsPlayerDependencies = defaultDependencies()) {
    this.dependencies = dependencies
  }

  status(messageId: string): PlaygroundTtsStatus {
    return this.statuses.get(messageId) || 'idle'
  }

  error(messageId: string): string {
    return this.errors.get(messageId) || ''
  }

  remember(messageId: string, objectUrl: string): void {
    const previous = this.urls.get(messageId)
    if (previous && previous !== objectUrl) this.dependencies.revokeObjectURL(previous)
    this.urls.set(messageId, objectUrl)
    this.setState(messageId, 'idle')
  }

  async synthesizeAndPlay(messageId: string, synthesize: () => Promise<Blob>): Promise<void> {
    let objectUrl = this.urls.get(messageId)
    if (!objectUrl) {
      this.setState(messageId, 'loading')
      try {
        objectUrl = this.dependencies.createObjectURL(await synthesize())
        this.urls.set(messageId, objectUrl)
      } catch (error) {
        const detail = error instanceof Error ? error.message : '语音生成失败'
        this.setState(messageId, 'error', detail)
        throw error
      }
    }
    await this.play(messageId, objectUrl)
  }

  stop(): void {
    if (!this.activeAudio) return
    this.activeAudio.pause()
    this.activeAudio.currentTime = 0
    const messageId = this.activeMessageId
    this.activeAudio = null
    this.activeMessageId = ''
    if (messageId) this.setState(messageId, 'idle')
  }

  stopAndClear(): void {
    this.stop()
    for (const objectUrl of this.urls.values()) this.dependencies.revokeObjectURL(objectUrl)
    const ids = new Set([...this.urls.keys(), ...this.statuses.keys()])
    this.urls.clear()
    this.statuses.clear()
    this.errors.clear()
    for (const id of ids) this.dependencies.onChange?.(id, 'idle')
  }

  private async play(messageId: string, objectUrl: string): Promise<void> {
    this.stop()
    const audio = this.dependencies.createAudio(objectUrl)
    this.activeAudio = audio
    this.activeMessageId = messageId
    audio.onended = () => {
      if (this.activeAudio !== audio) return
      this.activeAudio = null
      this.activeMessageId = ''
      this.setState(messageId, 'idle')
    }
    audio.onerror = () => {
      if (this.activeAudio !== audio) return
      this.activeAudio = null
      this.activeMessageId = ''
      this.setState(messageId, 'error', '音频播放失败')
    }
    this.setState(messageId, 'playing')
    try {
      await audio.play()
    } catch (error) {
      this.activeAudio = null
      this.activeMessageId = ''
      const detail = error instanceof Error ? error.message : '音频播放失败'
      this.setState(messageId, 'error', detail)
      throw error
    }
  }

  private setState(messageId: string, status: PlaygroundTtsStatus, error = ''): void {
    this.statuses.set(messageId, status)
    if (error) this.errors.set(messageId, error)
    else this.errors.delete(messageId)
    this.dependencies.onChange?.(messageId, status, error || undefined)
  }
}
