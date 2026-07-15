import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'

import { getLivePreferences, saveLivePreferences } from '@/api/live'
import type { LivePreferences, LiveServerEvent, LiveSessionStart } from '@/api/live-types'
import { LiveSocketClient } from '@/live/LiveSocketClient'
import { MicrophoneCapture } from '@/live/MicrophoneCapture'
import { PcmStreamPlayer } from '@/live/PcmStreamPlayer'
import { applyLiveEvent, createLiveState } from '@/live/live-state'

interface LiveSocketLike {
  connect(userId: string, start: LiveSessionStart): Promise<void>
  sendAudio(pcm: ArrayBuffer): void
  close(): void
}

interface MicrophoneLike {
  start(onPcm: (pcm: ArrayBuffer) => void): Promise<void>
  setMuted(muted: boolean): void
  stop(): Promise<void>
}

interface PlayerLike {
  start(): Promise<void>
  enqueue(pcm: ArrayBuffer): void
  clear(): void
  stop(): Promise<void>
}

export interface LiveSocketCallbacks {
  onEvent(event: LiveServerEvent): void
  onAudio(pcm: ArrayBuffer): void
  onClose(): void
  onError(): void
}

export interface LiveRuntimeDependencies {
  loadPreferences(userId: string): Promise<LivePreferences>
  savePreferences(
    userId: string,
    preferences: Omit<LivePreferences, 'user_id'>,
  ): Promise<LivePreferences>
  createSocket(callbacks: LiveSocketCallbacks): LiveSocketLike
  microphone: MicrophoneLike
  player: PlayerLike
}

const DEFAULT_PREFERENCES: LivePreferences = {
  user_id: '',
  model: 'qwen-audio-3.0-realtime-flash',
  voice: 'longanqian',
  instructions: '你是一位自然、简洁的实时语音助手。请使用适合口语朗读的纯文本回答。',
}

function browserDependencies(): LiveRuntimeDependencies {
  return {
    loadPreferences: getLivePreferences,
    savePreferences: saveLivePreferences,
    createSocket: (callbacks) => new LiveSocketClient(callbacks),
    microphone: new MicrophoneCapture(),
    player: new PcmStreamPlayer(),
  }
}

export function createLiveRuntime(dependencies: LiveRuntimeDependencies = browserDependencies()) {
  const state = reactive(createLiveState())
  const preferences = ref<LivePreferences>({ ...DEFAULT_PREFERENCES })
  const loading = ref(false)
  const saving = ref(false)
  const muted = ref(false)
  let ready = false

  const socket = dependencies.createSocket({
    onEvent(event) {
      if (event.type === 'session.ready') ready = true
      if (event.type === 'session.closed' || event.type === 'session.error') ready = false
      const effect = applyLiveEvent(state, event)
      if (effect.clearPlayback) dependencies.player.clear()
    },
    onAudio(pcm) {
      dependencies.player.enqueue(pcm)
    },
    onClose() {
      ready = false
      if (state.phase !== 'error' && state.phase !== 'ending') state.phase = 'idle'
    },
    onError() {
      ready = false
      if (state.phase !== 'error') {
        state.phase = 'error'
        state.error = 'Live 实时连接异常，请重新开始通话'
        state.errorCode = 'socket_error'
        state.recoverable = true
      }
    },
  })

  const isActive = computed(() => !['idle', 'error'].includes(state.phase))
  const canEditSettings = computed(() => !isActive.value)
  const statusLabel = computed(() => {
    const labels = {
      idle: '准备就绪',
      connecting: '正在连接声场',
      listening: muted.value ? '麦克风已静音' : '正在聆听',
      thinking: '正在理解',
      speaking: '正在回应',
      ending: '正在结束通话',
      error: '连接异常',
    }
    return labels[state.phase]
  })

  async function loadPreferences(userId: string): Promise<void> {
    loading.value = true
    try {
      preferences.value = await dependencies.loadPreferences(userId)
    } finally {
      loading.value = false
    }
  }

  async function persistPreferences(userId: string): Promise<void> {
    if (!canEditSettings.value) return
    saving.value = true
    try {
      const { user_id: _userId, ...editable } = preferences.value
      preferences.value = await dependencies.savePreferences(userId, editable)
    } finally {
      saving.value = false
    }
  }

  async function startCall(userId: string): Promise<void> {
    if (isActive.value) return
    state.phase = 'connecting'
    state.error = ''
    state.errorCode = ''
    state.transcripts.splice(0)
    ready = false
    muted.value = false
    try {
      await dependencies.player.start()
      await dependencies.microphone.start((pcm) => {
        if (ready && !muted.value) socket.sendAudio(pcm)
      })
      await socket.connect(userId, {
        type: 'session.start',
        model: preferences.value.model,
        voice: preferences.value.voice,
        instructions: preferences.value.instructions,
      })
    } catch (error) {
      ready = false
      state.phase = 'error'
      state.error = error instanceof Error ? error.message : '无法开始 Live 通话'
      state.errorCode = 'start_failed'
      state.recoverable = true
      socket.close()
      await dependencies.microphone.stop()
      await dependencies.player.stop()
    }
  }

  async function endCall(): Promise<void> {
    if (state.phase === 'idle') return
    state.phase = 'ending'
    ready = false
    socket.close()
    await Promise.all([dependencies.microphone.stop(), dependencies.player.stop()])
    state.phase = 'idle'
    muted.value = false
  }

  function toggleMute(): void {
    if (!isActive.value) return
    muted.value = !muted.value
    dependencies.microphone.setMuted(muted.value)
  }

  function clearTranscripts(): void {
    if (!isActive.value) state.transcripts.splice(0)
  }

  return {
    state,
    preferences,
    loading,
    saving,
    muted,
    isActive,
    canEditSettings,
    statusLabel,
    loadPreferences,
    persistPreferences,
    startCall,
    endCall,
    toggleMute,
    clearTranscripts,
  }
}

export const useLiveStore = defineStore('live', () => createLiveRuntime())
