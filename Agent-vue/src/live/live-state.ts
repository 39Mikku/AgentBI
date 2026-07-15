import type { LiveServerEvent } from '@/api/live-types'

export type LivePhase =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'ending'
  | 'error'

export interface LiveTranscript {
  id: string
  messageId?: string
  role: 'user' | 'assistant'
  text: string
  stash: string
  final: boolean
  interrupted: boolean
  status: 'streaming' | 'complete' | 'interrupted'
}

export interface LiveState {
  phase: LivePhase
  transcripts: LiveTranscript[]
  error: string
  errorCode: string
  recoverable: boolean
}

export interface LiveEventEffect {
  clearPlayback: boolean
}

export function createLiveState(): LiveState {
  return {
    phase: 'idle',
    transcripts: [],
    error: '',
    errorCode: '',
    recoverable: false,
  }
}

function transcript(
  state: LiveState,
  id: string,
  role: LiveTranscript['role'],
): LiveTranscript {
  let item = state.transcripts.find((entry) => entry.id === id)
  if (!item) {
    item = {
      id,
      role,
      text: '',
      stash: '',
      final: false,
      interrupted: false,
      status: 'streaming',
    }
    state.transcripts.push(item)
  }
  return item
}

export function applyLiveEvent(state: LiveState, event: LiveServerEvent): LiveEventEffect {
  let clearPlayback = false
  switch (event.type) {
    case 'session.ready':
      state.phase = 'listening'
      state.error = ''
      break
    case 'state.listening':
      state.phase = 'listening'
      clearPlayback = true
      break
    case 'state.thinking':
      state.phase = 'thinking'
      break
    case 'state.speaking':
      state.phase = 'speaking'
      break
    case 'user.transcript.delta': {
      const item = transcript(state, event.item_id, 'user')
      item.text = event.text
      item.stash = event.stash || ''
      break
    }
    case 'user.transcript.final': {
      const item = transcript(state, event.item_id, 'user')
      item.text = event.transcript
      item.stash = ''
      item.final = true
      item.status = 'complete'
      item.messageId = event.message_id
      break
    }
    case 'assistant.transcript.delta': {
      const item = transcript(state, event.item_id, 'assistant')
      item.text += event.delta
      break
    }
    case 'assistant.transcript.final': {
      const item = transcript(state, event.item_id, 'assistant')
      item.text = event.transcript
      item.final = true
      item.status = 'complete'
      item.messageId = event.message_id
      break
    }
    case 'response.interrupted': {
      clearPlayback = true
      state.phase = 'listening'
      const latestAssistant = [...state.transcripts]
        .reverse()
        .find((item) => item.role === 'assistant' && !item.final)
      if (latestAssistant) {
        latestAssistant.interrupted = true
        latestAssistant.final = true
        latestAssistant.status = 'interrupted'
        latestAssistant.messageId = event.message_id
      }
      break
    }
    case 'response.completed':
      state.phase = 'listening'
      break
    case 'session.error':
      state.phase = 'error'
      state.error = event.message
      state.errorCode = event.code
      state.recoverable = event.recoverable
      break
    case 'session.closed':
      state.phase = 'idle'
      break
  }
  return { clearPlayback }
}
