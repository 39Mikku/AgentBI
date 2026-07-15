import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'

import * as api from '@/api/live'
import type {
  LiveConversation,
  LiveMessage,
  LivePreferences,
  LiveRole,
  LiveRoleMemory,
  LiveServerEvent,
  LiveSessionStart,
} from '@/api/live-types'
import { LiveSocketClient } from '@/live/LiveSocketClient'
import { MicrophoneCapture } from '@/live/MicrophoneCapture'
import { PcmStreamPlayer } from '@/live/PcmStreamPlayer'
import { applyLiveEvent, createLiveState, type LiveTranscript } from '@/live/live-state'

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

type RoleCreatePayload = Omit<LiveRole, 'id' | 'is_default' | 'created_at' | 'updated_at'>
type RoleUpdatePayload = Partial<Pick<LiveRole, 'name' | 'instructions' | 'voice' | 'avatar_data_url' | 'memory_enabled'>>

export interface LiveRuntimeDependencies {
  loadPreferences(userId: string): Promise<LivePreferences>
  savePreferences(userId: string, preferences: Omit<LivePreferences, 'user_id'>): Promise<LivePreferences>
  listRoles(userId: string): Promise<LiveRole[]>
  createRole(payload: RoleCreatePayload): Promise<LiveRole>
  updateRole(roleId: string, userId: string, payload: RoleUpdatePayload): Promise<LiveRole>
  deleteRole(roleId: string, userId: string): Promise<void>
  getRoleMemory(roleId: string, userId: string): Promise<LiveRoleMemory>
  saveRoleMemory(roleId: string, userId: string, content: string): Promise<LiveRoleMemory>
  clearRoleMemory(roleId: string, userId: string): Promise<void>
  refreshRoleMemory(roleId: string, userId: string): Promise<LiveRoleMemory>
  listConversations(userId: string, roleId: string): Promise<LiveConversation[]>
  createConversation(payload: { user_id: string; role_id: string; title?: string }): Promise<LiveConversation>
  updateConversation(conversationId: string, userId: string, title: string): Promise<LiveConversation>
  deleteConversation(conversationId: string, userId: string): Promise<void>
  listMessages(userId: string, conversationId: string): Promise<LiveMessage[]>
  delay(milliseconds: number): Promise<void>
  createSocket(callbacks: LiveSocketCallbacks): LiveSocketLike
  microphone: MicrophoneLike
  player: PlayerLike
}

const DEFAULT_PREFERENCES: LivePreferences = {
  user_id: '',
  model: 'qwen-audio-3.0-realtime-flash',
  history_context_turns: 12,
  max_history_turns: 20,
}

function browserDependencies(): LiveRuntimeDependencies {
  return {
    loadPreferences: api.getLivePreferences,
    savePreferences: api.saveLivePreferences,
    listRoles: api.listLiveRoles,
    createRole: api.createLiveRole,
    updateRole: api.updateLiveRole,
    deleteRole: api.deleteLiveRole,
    getRoleMemory: api.getLiveRoleMemory,
    saveRoleMemory: api.saveLiveRoleMemory,
    clearRoleMemory: api.clearLiveRoleMemory,
    refreshRoleMemory: api.refreshLiveRoleMemory,
    listConversations: api.listLiveConversations,
    createConversation: api.createLiveConversation,
    updateConversation: api.updateLiveConversation,
    deleteConversation: api.deleteLiveConversation,
    listMessages: api.listLiveMessages,
    delay: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
    createSocket: (callbacks) => new LiveSocketClient(callbacks),
    microphone: new MicrophoneCapture(),
    player: new PcmStreamPlayer(),
  }
}

function storageGet(key: string): string | null {
  return typeof localStorage === 'undefined' ? null : localStorage.getItem(key)
}

function storageSet(key: string, value: string): void {
  if (typeof localStorage !== 'undefined') localStorage.setItem(key, value)
}

function roleStorageKey(userId: string): string {
  return `agentbi_live_role:${userId}`
}

function conversationStorageKey(userId: string, roleId: string): string {
  return `agentbi_live_conversation:${userId}:${roleId}`
}

function messageToTranscript(message: LiveMessage): LiveTranscript {
  return {
    id: message.item_id,
    messageId: message.id,
    role: message.role,
    text: message.content,
    stash: '',
    final: true,
    interrupted: message.status === 'interrupted',
    status: message.status,
  }
}

const DEFAULT_LIVE_TITLES = new Set(['新语音会话', '未命名会话'])

export function createLiveRuntime(dependencies: LiveRuntimeDependencies = browserDependencies()) {
  const state = reactive(createLiveState())
  const preferences = ref<LivePreferences>({ ...DEFAULT_PREFERENCES })
  const roles = ref<LiveRole[]>([])
  const conversations = ref<LiveConversation[]>([])
  const roleMemory = ref<LiveRoleMemory | null>(null)
  const activeRoleId = ref('')
  const activeConversationId = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const muted = ref(false)
  let currentUserId = ''
  let ready = false

  const currentRole = computed(() => roles.value.find((item) => item.id === activeRoleId.value) || null)
  const currentConversation = computed(() => conversations.value.find((item) => item.id === activeConversationId.value) || null)
  const isActive = computed(() => !['idle', 'error'].includes(state.phase))
  const canEditSettings = computed(() => !isActive.value)
  const statusLabel = computed(() => ({
    idle: '准备就绪', connecting: '正在连接声场',
    listening: muted.value ? '麦克风已静音' : '正在聆听',
    thinking: '正在理解', speaking: '正在回应', ending: '正在结束通话', error: '连接异常',
  })[state.phase])

  function setMessages(messages: LiveMessage[]): void {
    state.transcripts.splice(0, state.transcripts.length, ...messages.map(messageToTranscript))
  }

  const socket = dependencies.createSocket({
    onEvent(event) {
      if (event.type === 'session.ready') ready = true
      if (event.type === 'session.closed' || event.type === 'session.error') ready = false
      const effect = applyLiveEvent(state, event)
      if (effect.clearPlayback) dependencies.player.clear()
    },
    onAudio(pcm) { dependencies.player.enqueue(pcm) },
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

  async function loadMessages(userId: string, conversationId: string): Promise<void> {
    setMessages(conversationId ? await dependencies.listMessages(userId, conversationId) : [])
  }

  async function loadConversations(userId: string, roleId: string): Promise<void> {
    conversations.value = await dependencies.listConversations(userId, roleId)
    const restored = storageGet(conversationStorageKey(userId, roleId))
    const selected = conversations.value.find((item) => item.id === restored) || conversations.value[0]
    activeConversationId.value = selected?.id || ''
    if (selected) storageSet(conversationStorageKey(userId, roleId), selected.id)
    await loadMessages(userId, activeConversationId.value)
  }

  async function loadWorkspace(userId: string): Promise<void> {
    currentUserId = userId
    loading.value = true
    try {
      const [loadedPreferences, loadedRoles] = await Promise.all([
        dependencies.loadPreferences(userId), dependencies.listRoles(userId),
      ])
      preferences.value = loadedPreferences
      roles.value = loadedRoles
      const restored = storageGet(roleStorageKey(userId))
      const selected = roles.value.find((item) => item.id === restored)
        || roles.value.find((item) => item.is_default) || roles.value[0]
      activeRoleId.value = selected?.id || ''
      if (selected) {
        storageSet(roleStorageKey(userId), selected.id)
        await Promise.all([
          loadConversations(userId, selected.id),
          dependencies.getRoleMemory(selected.id, userId).then((value) => { roleMemory.value = value }),
        ])
      }
    } finally { loading.value = false }
  }

  async function selectRole(roleId: string, userId = currentUserId): Promise<void> {
    if (isActive.value || !roles.value.some((item) => item.id === roleId)) return
    activeRoleId.value = roleId
    storageSet(roleStorageKey(userId), roleId)
    await Promise.all([
      loadConversations(userId, roleId),
      dependencies.getRoleMemory(roleId, userId).then((value) => { roleMemory.value = value }),
    ])
  }

  async function selectConversation(conversationId: string, userId = currentUserId): Promise<void> {
    if (isActive.value || !conversations.value.some((item) => item.id === conversationId)) return
    activeConversationId.value = conversationId
    storageSet(conversationStorageKey(userId, activeRoleId.value), conversationId)
    await loadMessages(userId, conversationId)
  }

  async function newConversation(userId = currentUserId): Promise<LiveConversation | null> {
    if (isActive.value || !activeRoleId.value) return null
    const created = await dependencies.createConversation({ user_id: userId, role_id: activeRoleId.value })
    conversations.value.unshift(created)
    activeConversationId.value = created.id
    storageSet(conversationStorageKey(userId, activeRoleId.value), created.id)
    setMessages([])
    return created
  }

  async function renameConversation(conversationId: string, title: string, userId = currentUserId): Promise<void> {
    if (isActive.value) return
    const updated = await dependencies.updateConversation(conversationId, userId, title)
    const index = conversations.value.findIndex((item) => item.id === conversationId)
    if (index >= 0) conversations.value[index] = updated
  }

  async function removeConversation(conversationId: string, userId = currentUserId): Promise<void> {
    if (isActive.value) return
    await dependencies.deleteConversation(conversationId, userId)
    conversations.value = conversations.value.filter((item) => item.id !== conversationId)
    if (activeConversationId.value === conversationId) {
      activeConversationId.value = conversations.value[0]?.id || ''
      await loadMessages(userId, activeConversationId.value)
    }
  }

  async function persistPreferences(userId = currentUserId): Promise<void> {
    if (!canEditSettings.value) return
    saving.value = true
    try {
      const { user_id: _userId, ...editable } = preferences.value
      preferences.value = await dependencies.savePreferences(userId, editable)
    } finally { saving.value = false }
  }

  async function createRole(payload: RoleCreatePayload): Promise<LiveRole> {
    const created = await dependencies.createRole(payload)
    roles.value.push(created)
    return created
  }

  async function persistRole(roleId: string, fields: RoleUpdatePayload, userId = currentUserId): Promise<void> {
    if (!canEditSettings.value) return
    const updated = await dependencies.updateRole(roleId, userId, fields)
    const index = roles.value.findIndex((item) => item.id === roleId)
    if (index >= 0) roles.value[index] = updated
  }

  async function removeRole(roleId: string, userId = currentUserId): Promise<void> {
    if (isActive.value) return
    await dependencies.deleteRole(roleId, userId)
    roles.value = roles.value.filter((item) => item.id !== roleId)
    const next = roles.value.find((item) => item.is_default) || roles.value[0]
    if (next) await selectRole(next.id, userId)
  }

  async function persistRoleMemory(content: string, userId = currentUserId): Promise<void> {
    if (!activeRoleId.value) return
    roleMemory.value = await dependencies.saveRoleMemory(activeRoleId.value, userId, content)
  }

  async function clearRoleMemory(userId = currentUserId): Promise<void> {
    if (!activeRoleId.value) return
    await dependencies.clearRoleMemory(activeRoleId.value, userId)
    roleMemory.value = await dependencies.getRoleMemory(activeRoleId.value, userId)
  }

  async function refreshRoleMemory(userId = currentUserId): Promise<void> {
    if (!activeRoleId.value) return
    roleMemory.value = await dependencies.refreshRoleMemory(activeRoleId.value, userId)
  }

  async function startCall(userId = currentUserId): Promise<void> {
    if (isActive.value || !activeRoleId.value) return
    if (!activeConversationId.value) await newConversation(userId)
    if (!activeConversationId.value) return
    state.phase = 'connecting'
    state.error = ''
    state.errorCode = ''
    ready = false
    muted.value = false
    try {
      await dependencies.player.start()
      await dependencies.microphone.start((pcm) => {
        if (ready && !muted.value) socket.sendAudio(pcm)
      })
      await socket.connect(userId, {
        type: 'session.start', role_id: activeRoleId.value,
        conversation_id: activeConversationId.value,
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
    if (currentUserId && activeConversationId.value) {
      const conversationId = activeConversationId.value
      const roleId = activeRoleId.value
      await Promise.all([
        loadMessages(currentUserId, conversationId),
        dependencies.listConversations(currentUserId, roleId).then((value) => { conversations.value = value }),
      ])
      for (let attempt = 0; attempt < 6; attempt += 1) {
        const selected = conversations.value.find((item) => item.id === conversationId)
        if (!selected || !DEFAULT_LIVE_TITLES.has(selected.title)) break
        await dependencies.delay(500)
        conversations.value = await dependencies.listConversations(currentUserId, roleId)
      }
    }
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
    state, preferences, roles, conversations, roleMemory,
    activeRoleId, activeConversationId, currentRole, currentConversation,
    loading, saving, muted, isActive, canEditSettings, statusLabel,
    loadWorkspace, selectRole, selectConversation, newConversation,
    renameConversation, removeConversation, persistPreferences,
    createRole, persistRole, removeRole, persistRoleMemory,
    clearRoleMemory, refreshRoleMemory, startCall, endCall,
    toggleMute, clearTranscripts,
  }
}

export const useLiveStore = defineStore('live', () => createLiveRuntime())
