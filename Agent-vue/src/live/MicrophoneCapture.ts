import { floatToInt16, resampleFloat32 } from './pcm'

interface MediaStreamLike {
  getTracks(): Array<{ stop(): void }>
}

interface AudioPortLike {
  onmessage: ((event: MessageEvent<Float32Array>) => void) | null
  postMessage(message: unknown, transfer?: Transferable[]): void
}

interface AudioNodeLike {
  connect(destination: unknown): unknown
  disconnect(): void
}

interface WorkletNodeLike extends AudioNodeLike {
  port: AudioPortLike
}

interface GainNodeLike extends AudioNodeLike {
  gain: { value: number }
}

interface AudioContextLike {
  sampleRate: number
  destination: unknown
  audioWorklet: { addModule(url: string): Promise<void> }
  createMediaStreamSource(stream: MediaStreamLike): AudioNodeLike
  createGain(): GainNodeLike
  resume(): Promise<void>
  close(): Promise<void>
}

export interface MicrophoneDependencies {
  getUserMedia(constraints: MediaStreamConstraints): Promise<MediaStreamLike>
  createAudioContext(options?: AudioContextOptions): AudioContextLike
  createWorkletNode(context: AudioContextLike, name: string): WorkletNodeLike
}

function browserDependencies(): MicrophoneDependencies {
  return {
    getUserMedia: (constraints) => navigator.mediaDevices.getUserMedia(constraints),
    createAudioContext: (options) => new AudioContext(options),
    createWorkletNode: (context, name) =>
      new AudioWorkletNode(context as unknown as BaseAudioContext, name),
  }
}

export class MicrophoneCapture {
  private readonly dependencies: MicrophoneDependencies
  private stream: MediaStreamLike | null = null
  private context: AudioContextLike | null = null
  private source: AudioNodeLike | null = null
  private node: WorkletNodeLike | null = null
  private silentGain: GainNodeLike | null = null
  private muted = false

  constructor(dependencies: MicrophoneDependencies = browserDependencies()) {
    this.dependencies = dependencies
  }

  async start(onPcm: (pcm: ArrayBuffer) => void): Promise<void> {
    if (this.context) return
    this.stream = await this.dependencies.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    this.context = this.dependencies.createAudioContext({ latencyHint: 'interactive' })
    await this.context.audioWorklet.addModule('/worklets/microphone-processor.js')
    await this.context.resume()
    this.source = this.context.createMediaStreamSource(this.stream)
    this.node = this.dependencies.createWorkletNode(this.context, 'agentbi-microphone')
    this.silentGain = this.context.createGain()
    this.silentGain.gain.value = 0
    this.source.connect(this.node)
    this.node.connect(this.silentGain)
    this.silentGain.connect(this.context.destination)
    this.node.port.onmessage = (event) => {
      if (this.muted || !this.context) return
      const resampled = resampleFloat32(event.data, this.context.sampleRate, 16000)
      const pcm = floatToInt16(resampled)
      const buffer = pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength) as ArrayBuffer
      onPcm(buffer)
    }
  }

  setMuted(muted: boolean): void {
    this.muted = muted
  }

  async stop(): Promise<void> {
    if (this.node) this.node.port.onmessage = null
    this.source?.disconnect()
    this.node?.disconnect()
    this.silentGain?.disconnect()
    for (const track of this.stream?.getTracks() || []) track.stop()
    const context = this.context
    this.stream = null
    this.context = null
    this.source = null
    this.node = null
    this.silentGain = null
    this.muted = false
    if (context) await context.close()
  }
}
