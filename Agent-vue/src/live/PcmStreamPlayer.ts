interface PlayerPortLike {
  postMessage(message: unknown, transfer?: Transferable[]): void
}

interface PlayerNodeLike {
  port: PlayerPortLike
  connect(destination: unknown): unknown
  disconnect(): void
}

interface PlayerContextLike {
  sampleRate: number
  destination: unknown
  audioWorklet: { addModule(url: string): Promise<void> }
  resume(): Promise<void>
  close(): Promise<void>
}

export interface PlayerDependencies {
  createAudioContext(options?: AudioContextOptions): PlayerContextLike
  createWorkletNode(context: PlayerContextLike, name: string): PlayerNodeLike
}

function browserDependencies(): PlayerDependencies {
  return {
    createAudioContext: (options) => new AudioContext(options),
    createWorkletNode: (context, name) =>
      new AudioWorkletNode(context as unknown as BaseAudioContext, name),
  }
}

export class PcmStreamPlayer {
  private readonly dependencies: PlayerDependencies
  private context: PlayerContextLike | null = null
  private node: PlayerNodeLike | null = null

  constructor(dependencies: PlayerDependencies = browserDependencies()) {
    this.dependencies = dependencies
  }

  async start(): Promise<void> {
    if (this.context) return
    this.context = this.dependencies.createAudioContext({
      latencyHint: 'interactive',
      sampleRate: 24000,
    })
    await this.context.audioWorklet.addModule('/worklets/pcm-player-processor.js')
    await this.context.resume()
    this.node = this.dependencies.createWorkletNode(this.context, 'agentbi-pcm-player')
    this.node.connect(this.context.destination)
  }

  enqueue(pcm: ArrayBuffer): void {
    if (!this.node) return
    this.node.port.postMessage({ type: 'enqueue', pcm, sourceRate: 24000 }, [pcm])
  }

  clear(): void {
    this.node?.port.postMessage({ type: 'clear' })
  }

  async stop(): Promise<void> {
    this.clear()
    this.node?.disconnect()
    const context = this.context
    this.node = null
    this.context = null
    if (context) await context.close()
  }
}
