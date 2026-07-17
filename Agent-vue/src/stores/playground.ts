import { computed, nextTick, reactive, ref, watch } from 'vue'
import { acceptHMRUpdate, defineStore } from 'pinia'

import * as api from '@/api/playground'
import type {
  PlaygroundConversation,
  PlaygroundMessage,
  PlaygroundPreferences,
  PlaygroundProfile,
  PlaygroundProfileType,
  PlaygroundStateTemplates,
  PlaygroundStreamEvent,
  PlaygroundSummary,
} from '@/api/playground-types'
import { applyPlaygroundStreamEvent } from '@/playground/stream-events'
import {
  ConversationGenerationTracker,
  hasGeneratingConversation,
} from '@/utils/conversation-generation'
import { replaceTimelineBranch } from '@/utils/message-branch'


const DEFAULT_PREFERENCES: PlaygroundPreferences = {
  temperature: 1,
  contextTurns: 24,
  thinkingLevel: 'medium',
  summaryTriggerMessages: 24,
  summaryRetainMessages: 8,
}


export const usePlaygroundStore = defineStore('playground', () => {
  const mode = ref<PlaygroundProfileType>('character')
  const profiles = ref<PlaygroundProfile[]>([])
  const activeProfileId = ref('')
  const conversations = ref<PlaygroundConversation[]>([])
  const activeConversationId = ref('')
  const messages = ref<PlaygroundMessage[]>([])
  const preferences = ref<PlaygroundPreferences>({ ...DEFAULT_PREFERENCES })
  const stateTemplates = ref<PlaygroundStateTemplates | null>(null)
  const summary = ref<PlaygroundSummary | null>(null)
  const loading = ref(false)
  const syncMessage = ref('')
  const error = ref('')
  const generatingConversationIds = ref<string[]>([])

  const generationTracker = new ConversationGenerationTracker()
  const controllers = new Map<string, AbortController>()
  let currentUserId = ''
  let preferenceTimer: ReturnType<typeof setTimeout> | null = null
  let summaryTimer: ReturnType<typeof setTimeout> | null = null

  const activeProfile = computed(
    () => profiles.value.find((item) => item.id === activeProfileId.value) || null,
  )
  const activeConversation = computed(
    () => conversations.value.find((item) => item.id === activeConversationId.value) || null,
  )
  const visibleProfiles = computed(() =>
    profiles.value.filter((item) => item.profile_type === mode.value),
  )
  const generating = computed(() => generatingConversationIds.value.length > 0)
  const activeGenerating = computed(() =>
    hasGeneratingConversation(generatingConversationIds.value, activeConversationId.value),
  )
  const isSyncing = computed(() => Boolean(syncMessage.value))

  function isConversationGenerating(conversationId: string) {
    return hasGeneratingConversation(generatingConversationIds.value, conversationId)
  }

  function markGenerating(conversationId: string, active: boolean) {
    if (active) generationTracker.start(conversationId)
    else generationTracker.finish(conversationId)
    generatingConversationIds.value = generationTracker.ids()
  }

  function modeKey(userId: string) {
    return `agentbi_playground:mode:${userId}`
  }

  function profileKey(userId: string, profileType: PlaygroundProfileType) {
    return `agentbi_playground:profile:${userId}:${profileType}`
  }

  function conversationKey(userId: string, profileId: string) {
    return `agentbi_playground:conversation:${userId}:${profileId}`
  }

  async function restorePreferences(userId: string) {
    currentUserId = userId
    preferences.value = await api.getPlaygroundPreferences(userId)
  }

  async function persistPreferences() {
    if (!currentUserId) return
    preferences.value = await api.savePlaygroundPreferences(
      currentUserId,
      preferences.value,
    )
  }

  watch(
    preferences,
    () => {
      if (!currentUserId) return
      if (preferenceTimer) clearTimeout(preferenceTimer)
      preferenceTimer = setTimeout(() => void persistPreferences(), 300)
    },
    { deep: true },
  )

  async function load(userId: string) {
    currentUserId = userId
    loading.value = true
    syncMessage.value = '正在进入 Playground…'
    error.value = ''
    try {
      await nextTick()
      const storedMode = localStorage.getItem(modeKey(userId))
      mode.value = storedMode === 'world' ? 'world' : 'character'
      const [storedPreferences, storedProfiles, templates] = await Promise.all([
        api.getPlaygroundPreferences(userId),
        api.listPlaygroundProfiles(userId),
        api.getPlaygroundStateTemplates(),
      ])
      preferences.value = storedPreferences
      profiles.value = storedProfiles
      stateTemplates.value = templates
      const restoredId = localStorage.getItem(profileKey(userId, mode.value))
      const target =
        visibleProfiles.value.find((item) => item.id === restoredId) || visibleProfiles.value[0]
      if (target) await selectProfile(target.id, userId)
      else clearWorkspace()
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '加载 Playground 失败'
    } finally {
      loading.value = false
      syncMessage.value = ''
    }
  }

  function clearWorkspace() {
    activeProfileId.value = ''
    conversations.value = []
    activeConversationId.value = ''
    messages.value = []
    summary.value = null
    stopSummaryPolling()
  }

  async function setMode(profileType: PlaygroundProfileType, userId = currentUserId) {
    if (mode.value === profileType && activeProfile.value?.profile_type === profileType) return
    mode.value = profileType
    localStorage.setItem(modeKey(userId), profileType)
    const restoredId = localStorage.getItem(profileKey(userId, profileType))
    const target =
      profiles.value.find(
        (item) => item.profile_type === profileType && item.id === restoredId,
      ) || profiles.value.find((item) => item.profile_type === profileType)
    if (target) await selectProfile(target.id, userId)
    else clearWorkspace()
  }

  async function selectProfile(profileId: string, userId = currentUserId) {
    const profile = profiles.value.find((item) => item.id === profileId)
    if (!profile) return
    syncMessage.value = `正在载入${profile.profile_type === 'character' ? '角色' : '世界'}…`
    try {
      await nextTick()
      currentUserId = userId
      mode.value = profile.profile_type
      activeProfileId.value = profile.id
      localStorage.setItem(modeKey(userId), profile.profile_type)
      localStorage.setItem(profileKey(userId, profile.profile_type), profile.id)
      conversations.value = await api.listPlaygroundConversations(
        userId,
        profile.id,
        profile.profile_type,
      )
      const restoredId = localStorage.getItem(conversationKey(userId, profile.id))
      const target =
        conversations.value.find((item) => item.id === restoredId) || conversations.value[0]
      if (target) await selectConversation(target.id, userId)
      else {
        activeConversationId.value = ''
        messages.value = []
        summary.value = null
        stopSummaryPolling()
      }
    } finally {
      syncMessage.value = ''
    }
  }

  async function reloadProfiles(userId = currentUserId) {
    profiles.value = await api.listPlaygroundProfiles(userId)
    return profiles.value
  }

  async function createProfile(
    payload: Omit<PlaygroundProfile, 'id' | 'created_at' | 'updated_at'>,
  ) {
    const profile = await api.createPlaygroundProfile(payload)
    profiles.value.unshift(profile)
    await selectProfile(profile.id, payload.user_id)
    return profile
  }

  async function updateProfile(
    profileId: string,
    payload: Partial<Omit<PlaygroundProfile, 'id' | 'user_id' | 'created_at' | 'updated_at'>>,
    userId = currentUserId,
  ) {
    const updated = await api.updatePlaygroundProfile(profileId, userId, payload)
    const index = profiles.value.findIndex((item) => item.id === profileId)
    if (index >= 0) profiles.value[index] = updated
    return updated
  }

  async function removeProfile(profileId: string, userId = currentUserId) {
    const profile = profiles.value.find((item) => item.id === profileId)
    await api.deletePlaygroundProfile(profileId, userId)
    profiles.value = profiles.value.filter((item) => item.id !== profileId)
    if (activeProfileId.value === profileId) {
      const next = profiles.value.find(
        (item) => item.profile_type === (profile?.profile_type || mode.value),
      )
      if (next) await selectProfile(next.id, userId)
      else clearWorkspace()
    }
  }

  async function createConversation(userId = currentUserId) {
    const profile = activeProfile.value
    if (!profile) throw new Error('请先选择角色或世界')
    syncMessage.value = '正在展开新的故事…'
    try {
      await nextTick()
      const conversation = await api.createPlaygroundConversation(
        userId,
        profile.id,
        profile.profile_type,
      )
      conversations.value.unshift(conversation)
      await selectConversation(conversation.id, userId)
      return conversation
    } finally {
      syncMessage.value = ''
    }
  }

  async function selectConversation(conversationId: string, userId = currentUserId) {
    stopSummaryPolling()
    const ownsSyncMessage = Boolean(syncMessage.value)
    if (!ownsSyncMessage) syncMessage.value = '正在载入故事…'
    try {
      if (!ownsSyncMessage) await nextTick()
      activeConversationId.value = conversationId
      if (activeProfileId.value) {
        localStorage.setItem(
          conversationKey(userId, activeProfileId.value),
          conversationId,
        )
      }
      const [storedMessages, storedSummary] = await Promise.all([
        api.listPlaygroundMessages(conversationId, userId),
        api.getPlaygroundSummary(conversationId, userId),
      ])
      if (activeConversationId.value !== conversationId) return
      messages.value = storedMessages.map((message) => ({ ...message, metadata: message.metadata || {} }))
      summary.value = storedSummary
      if (storedSummary.status === 'running') startSummaryPolling(conversationId, userId)
    } finally {
      if (!ownsSyncMessage) syncMessage.value = ''
    }
  }

  async function renameConversation(
    conversationId: string,
    title: string,
    userId = currentUserId,
  ) {
    const normalized = title.trim()
    if (!normalized) return
    const updated = await api.updatePlaygroundConversation(
      conversationId,
      userId,
      normalized,
    )
    const index = conversations.value.findIndex((item) => item.id === conversationId)
    if (index >= 0) conversations.value[index] = updated
  }

  async function removeConversation(conversationId: string, userId = currentUserId) {
    await api.deletePlaygroundConversation(conversationId, userId)
    conversations.value = conversations.value.filter((item) => item.id !== conversationId)
    if (activeConversationId.value === conversationId) {
      const next = conversations.value[0]
      if (next) await selectConversation(next.id, userId)
      else {
        activeConversationId.value = ''
        messages.value = []
        summary.value = null
        stopSummaryPolling()
      }
    }
  }

  function createStreamingMessage(userId: string, conversationId: string) {
    return reactive<PlaygroundMessage>({
      id: `temp-assistant-${Date.now()}`,
      conversation_id: conversationId,
      user_id: userId,
      role: 'assistant',
      content: '',
      reasoning_summary: null,
      tool_events: [],
      timeline: [],
      status: 'streaming',
      metadata: {},
    })
  }

  function consumeEvent(
    temporary: PlaygroundMessage,
    conversationId: string,
    event: PlaygroundStreamEvent,
  ) {
    const previousId = temporary.id
    applyPlaygroundStreamEvent(temporary, event)
    if (event.event === 'message_start') {
      const parent = messages.value.at(-2)
      if (
        activeConversationId.value === conversationId &&
        parent?.role === 'user' &&
        parent.id.startsWith('temp-user-') &&
        event.data.parent_message_id
      ) {
        parent.id = String(event.data.parent_message_id)
      }
      if (temporary.id !== previousId) {
        const conversation = conversations.value.find((item) => item.id === conversationId)
        if (conversation) conversation.active_message_id = temporary.id
      }
    } else if (event.event === 'conversation_title_updated') {
      const conversation = conversations.value.find(
        (item) => item.id === (event.data.conversation_id || conversationId),
      )
      if (conversation && event.data.title) conversation.title = String(event.data.title)
    } else if (event.event === 'summary_status') {
      if (activeConversationId.value === conversationId) {
        if (summary.value) summary.value.status = 'running'
        startSummaryPolling(conversationId, currentUserId)
      }
    } else if (event.event === 'error') {
      error.value = String(event.data.message || '生成失败')
    }
  }

  async function runGeneration(
    userId: string,
    conversationId: string,
    placeTemporary: () => PlaygroundMessage,
    start: (
      onEvent: (event: PlaygroundStreamEvent) => void,
      signal: AbortSignal,
    ) => Promise<void>,
  ) {
    const temporary = placeTemporary()
    const controller = new AbortController()
    controllers.set(conversationId, controller)
    markGenerating(conversationId, true)
    error.value = ''
    try {
      await start(
        (event) => consumeEvent(temporary, conversationId, event),
        controller.signal,
      )
    } catch (reason) {
      if ((reason as Error).name !== 'AbortError') {
        error.value = reason instanceof Error ? reason.message : '生成失败'
      }
      temporary.status = 'error'
    } finally {
      controllers.delete(conversationId)
      markGenerating(conversationId, false)
    }
  }

  async function send(userId: string, content: string) {
    const normalized = content.trim()
    if (!normalized || activeGenerating.value || !activeProfile.value) return
    if (!activeConversationId.value) await createConversation(userId)
    const conversationId = activeConversationId.value
    const previous = messages.value.at(-1)
    if (previous?.role === 'assistant') previous.metadata.action_options = []
    messages.value.push({
      id: `temp-user-${Date.now()}`,
      conversation_id: conversationId,
      user_id: userId,
      role: 'user',
      content: normalized,
      tool_events: [],
      timeline: [],
      status: 'complete',
      metadata: {},
    })
    await runGeneration(
      userId,
      conversationId,
      () => {
        const temporary = createStreamingMessage(userId, conversationId)
        messages.value.push(temporary)
        return temporary
      },
      (onEvent, signal) =>
        api.streamPlaygroundChat(
          {
            user_id: userId,
            conversation_id: conversationId,
            profile_id: activeProfileId.value,
            content: normalized,
          },
          onEvent,
          signal,
        ),
    )
  }

  async function retry(userId: string, messageId: string) {
    const conversationId = activeConversationId.value
    if (!conversationId || activeGenerating.value) return
    await runGeneration(
      userId,
      conversationId,
      () => {
        const original = messages.value.find((item) => item.id === messageId)
        const temporary = createStreamingMessage(userId, conversationId)
        if (original) {
          const versions = original.version_ids?.length ? original.version_ids : [original.id]
          const count = original.sibling_count || 1
          temporary.version_ids = [...versions, temporary.id]
          temporary.sibling_count = count + 1
          temporary.sibling_index = count
        }
        messages.value = replaceTimelineBranch(messages.value, messageId, [temporary])
        return temporary
      },
      (onEvent, signal) =>
        api.streamPlaygroundRetry(
          {
            user_id: userId,
            conversation_id: conversationId,
            profile_id: activeProfileId.value,
            message_id: messageId,
          },
          onEvent,
          signal,
        ),
    )
  }

  async function edit(userId: string, messageId: string, content: string) {
    const normalized = content.trim()
    const conversationId = activeConversationId.value
    if (!conversationId || activeGenerating.value || !normalized) return
    await runGeneration(
      userId,
      conversationId,
      () => {
        const original = messages.value.find((item) => item.id === messageId)
        const temporaryUser = reactive<PlaygroundMessage>({
          ...(original || {
            conversation_id: conversationId,
            user_id: userId,
            role: 'user' as const,
            tool_events: [],
          }),
          id: `temp-user-${Date.now()}`,
          content: normalized,
          status: 'complete',
          reasoning_summary: null,
          timeline: [],
          metadata: {},
        })
        const temporaryAssistant = createStreamingMessage(userId, conversationId)
        messages.value = replaceTimelineBranch(messages.value, messageId, [
          temporaryUser,
          temporaryAssistant,
        ])
        return temporaryAssistant
      },
      (onEvent, signal) =>
        api.streamPlaygroundEdit(
          {
            user_id: userId,
            conversation_id: conversationId,
            profile_id: activeProfileId.value,
            message_id: messageId,
            content: normalized,
          },
          onEvent,
          signal,
        ),
    )
  }

  async function selectVersion(messageId: string, userId = currentUserId) {
    const conversationId = activeConversationId.value
    if (!conversationId) return
    syncMessage.value = '正在切换故事版本…'
    try {
      await api.setPlaygroundActiveMessage(conversationId, userId, messageId)
      await selectConversation(conversationId, userId)
    } finally {
      syncMessage.value = ''
    }
  }

  async function branch(messageId: string, userId = currentUserId) {
    const conversationId = activeConversationId.value
    if (!conversationId) return
    syncMessage.value = '正在创建故事分支…'
    try {
      await nextTick()
      const created = await api.createPlaygroundBranch(
        conversationId,
        userId,
        messageId,
      )
      conversations.value.unshift(created)
      await selectConversation(created.id, userId)
    } finally {
      syncMessage.value = ''
    }
  }

  async function editOpening(messageId: string, content: string, userId = currentUserId) {
    if (!activeConversationId.value) return
    await api.editPlaygroundOpeningMessage(
      activeConversationId.value,
      userId,
      messageId,
      content,
    )
    await selectConversation(activeConversationId.value, userId)
  }

  async function chooseOption(text: string, userId = currentUserId) {
    await send(userId, text)
  }

  async function saveSummary(content: string, userId = currentUserId) {
    if (!activeConversationId.value) return
    summary.value = await api.savePlaygroundSummary(
      activeConversationId.value,
      userId,
      { content, status: 'idle', last_error: null },
    )
  }

  async function refreshSummary(userId = currentUserId) {
    if (!activeConversationId.value) return
    syncMessage.value = '正在精炼长会话…'
    try {
      summary.value = await api.refreshPlaygroundSummary(
        activeConversationId.value,
        userId,
      )
    } finally {
      syncMessage.value = ''
    }
  }

  function startSummaryPolling(conversationId: string, userId: string) {
    stopSummaryPolling()
    const poll = async () => {
      if (activeConversationId.value !== conversationId) return
      try {
        const current = await api.getPlaygroundSummary(conversationId, userId)
        if (activeConversationId.value !== conversationId) return
        summary.value = current
        if (current.status === 'running') summaryTimer = setTimeout(poll, 2000)
      } catch {
        summaryTimer = setTimeout(poll, 4000)
      }
    }
    summaryTimer = setTimeout(poll, 2000)
  }

  function stopSummaryPolling() {
    if (summaryTimer) clearTimeout(summaryTimer)
    summaryTimer = null
  }

  function stop(conversationId = activeConversationId.value) {
    controllers.get(conversationId)?.abort()
  }

  return {
    mode,
    profiles,
    visibleProfiles,
    activeProfileId,
    activeProfile,
    conversations,
    activeConversationId,
    activeId: activeConversationId,
    activeConversation,
    messages,
    preferences,
    stateTemplates,
    summary,
    loading,
    syncMessage,
    isSyncing,
    error,
    generating,
    activeGenerating,
    generatingConversationIds,
    isConversationGenerating,
    load,
    setMode,
    selectProfile,
    reloadProfiles,
    createProfile,
    updateProfile,
    removeProfile,
    restorePreferences,
    persistPreferences,
    createConversation,
    selectConversation,
    renameConversation,
    removeConversation,
    send,
    retry,
    edit,
    selectVersion,
    branch,
    editOpening,
    chooseOption,
    saveSummary,
    refreshSummary,
    stop,
  }
})


if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePlaygroundStore, import.meta.hot))
}
