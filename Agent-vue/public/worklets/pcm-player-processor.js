class AgentBiPcmPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.queue = []
    this.offset = 0
    this.port.onmessage = (event) => {
      if (event.data?.type === 'clear') {
        this.queue = []
        this.offset = 0
        return
      }
      if (event.data?.type !== 'enqueue' || !event.data.pcm) return
      const sourceRate = event.data.sourceRate || 24000
      const int16 = new Int16Array(event.data.pcm)
      const source = Float32Array.from(int16, (sample) => sample / (sample < 0 ? 32768 : 32767))
      this.queue.push(this.resample(source, sourceRate, sampleRate))
    }
  }

  resample(input, sourceRate, targetRate) {
    if (sourceRate === targetRate) return input
    const length = Math.max(1, Math.round((input.length * targetRate) / sourceRate))
    const output = new Float32Array(length)
    const step = sourceRate / targetRate
    for (let index = 0; index < length; index += 1) {
      const position = index * step
      const leftIndex = Math.min(Math.floor(position), input.length - 1)
      const rightIndex = Math.min(leftIndex + 1, input.length - 1)
      const mix = position - leftIndex
      output[index] = input[leftIndex] + (input[rightIndex] - input[leftIndex]) * mix
    }
    return output
  }

  process(_inputs, outputs) {
    const output = outputs[0]?.[0]
    if (!output) return true
    output.fill(0)
    let writeIndex = 0
    while (writeIndex < output.length && this.queue.length) {
      const current = this.queue[0]
      const available = current.length - this.offset
      const count = Math.min(available, output.length - writeIndex)
      output.set(current.subarray(this.offset, this.offset + count), writeIndex)
      writeIndex += count
      this.offset += count
      if (this.offset >= current.length) {
        this.queue.shift()
        this.offset = 0
      }
    }
    return true
  }
}

registerProcessor('agentbi-pcm-player', AgentBiPcmPlayerProcessor)
