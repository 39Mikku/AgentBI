import { computed, nextTick, reactive, ref, watch } from 'vue'
import { acceptHMRUpdate, defineStore } from 'pinia'
import * as api from '@/api/chat'
import * as assistantsApi from '@/api/assistants'
import type {
  AssistantProfile,
  ChatMessage,
  ChatPreferences,
  ChatRuntimeContext,
  ChatTimelineEvent,
  Conversation,
} from '@/api/chat-types'
import { replaceTimelineBranch } from '@/utils/message-branch'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const assistants = ref<AssistantProfile[]>([])
  const activeAssistantId = ref('')
  const messages = ref<ChatMessage[]>([])
  const activeId = ref('')
  const loading = ref(false)
  const generating = ref(false)
  const syncMessage = ref('')
  const error = ref('')
  const preferences = ref<ChatPreferences>({ temperature: 0.7, contextTurns: 8 })
  let controller: AbortController | null = null
  let currentUserId = ''
  let preferenceTimer: ReturnType<typeof setTimeout> | null = null
  const activeConversation = computed(
    () => conversations.value.find((item) => item.id === activeId.value) || null,
  )
  const activeAssistant = computed(
    () => assistants.value.find((item) => item.id === activeAssistantId.value) || null,
  )
  const isSyncing = computed(() => Boolean(syncMessage.value))

  function activeStorageKey(userId: string) {
    return `agentbi_active_conversation:${userId}`
  }
  function assistantStorageKey(userId: string) {
    return `agentbi_active_assistant:${userId}`
  }
  function assistantConversationStorageKey(userId: string, assistantId: string) {
    return `agentbi_active_conversation:${userId}:${assistantId}`
  }
  function saveActiveConversation(userId: string, id: string) {
    localStorage.setItem(activeStorageKey(userId), id)
  }
  function clearActiveConversation(userId: string) {
    localStorage.removeItem(activeStorageKey(userId))
  }

  async function restorePreferences(userId: string) {
    currentUserId = userId
    preferences.value = await api.getPreferences(userId)
  }

  async function persistPreferences() {
    if (currentUserId) await api.savePreferences(currentUserId, preferences.value)
  }

  watch(
    preferences,
    () => {
      if (!currentUserId) return
      if (preferenceTimer) clearTimeout(preferenceTimer)
      preferenceTimer = setTimeout(() => {
        void persistPreferences()
      }, 250)
    },
    { deep: true },
  )

  function appendTimeline(message: ChatMessage, event: ChatTimelineEvent) {
    message.timeline ||= []
    const previous = message.timeline.at(-1)
    if (
      (event.type === 'delta' || event.type === 'reasoning_summary') &&
      previous?.type === event.type
    ) {
      previous.content = `${previous.content || ''}${event.content || ''}`
    } else {
      message.timeline.push(event)
    }
  }

  async function load(userId: string) {
    loading.value = true
    syncMessage.value = '正在同步会话…'
    try {
      await nextTick()
      await restorePreferences(userId)
      assistants.value = await assistantsApi.listAssistants(userId)
      const restoredAssistantId = localStorage.getItem(assistantStorageKey(userId))
      const assistant =
        assistants.value.find((item) => item.id === restoredAssistantId) ||
        assistants.value.find((item) => item.is_default) ||
        assistants.value[0]
      activeAssistantId.value = assistant?.id || ''
      if (activeAssistantId.value)
        localStorage.setItem(assistantStorageKey(userId), activeAssistantId.value)
      conversations.value = activeAssistantId.value
        ? await api.listConversations(userId, activeAssistantId.value)
        : []
      const restoredId = activeAssistantId.value
        ? localStorage.getItem(assistantConversationStorageKey(userId, activeAssistantId.value))
        : localStorage.getItem(activeStorageKey(userId))
      const target =
        conversations.value.find((item) => item.id === restoredId) || conversations.value[0]
      if (target) {
        if (!preferences.value.providerId && target.provider_id) {
          preferences.value = {
            providerId: target.provider_id,
            model: target.model || undefined,
            temperature: target.temperature,
            contextTurns: target.context_turns,
          }
        }
        await select(target.id, userId)
      } else {
        activeId.value = ''
        messages.value = []
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载会话失败'
    } finally {
      loading.value = false
      syncMessage.value = ''
    }
  }
  async function create(userId: string) {
    currentUserId = userId
    syncMessage.value = '正在创建新会话…'
    try {
      await nextTick()
      const conversation = await api.createConversation({
        user_id: userId,
        title: '未命名会话',
        temperature: preferences.value.temperature,
        context_turns: preferences.value.contextTurns,
        provider_id: preferences.value.providerId,
        model: preferences.value.model,
        assistant_id: activeAssistantId.value || undefined,
      })
      conversations.value.unshift(conversation)
      activeId.value = conversation.id
      messages.value = []
      saveActiveConversation(userId, conversation.id)
      if (activeAssistantId.value)
        localStorage.setItem(
          assistantConversationStorageKey(userId, activeAssistantId.value),
          conversation.id,
        )
    } finally {
      syncMessage.value = ''
    }
  }
  async function select(id: string, userId: string) {
    const ownsMessage = Boolean(syncMessage.value)
    if (!ownsMessage) syncMessage.value = '正在加载会话…'
    try {
      if (!ownsMessage) await nextTick()
      currentUserId = userId
      activeId.value = id
      saveActiveConversation(userId, id)
      if (activeAssistantId.value)
        localStorage.setItem(assistantConversationStorageKey(userId, activeAssistantId.value), id)
      messages.value = await api.listMessages(id, userId)
    } finally {
      if (!ownsMessage) syncMessage.value = ''
    }
  }
  async function rename(id: string, userId: string, title: string) {
    const normalized = title.trim()
    if (!normalized) return
    const updated = await api.updateConversation(id, userId, { title: normalized })
    const index = conversations.value.findIndex((item) => item.id === id)
    if (index !== -1) conversations.value[index] = updated
  }

  async function selectAssistant(assistantId: string, userId: string) {
    if (!assistants.value.some((assistant) => assistant.id === assistantId)) return
    syncMessage.value = '正在切换助手…'
    try {
      await nextTick()
      currentUserId = userId
      activeAssistantId.value = assistantId
      localStorage.setItem(assistantStorageKey(userId), assistantId)
      conversations.value = await api.listConversations(userId, assistantId)
      const restoredId = localStorage.getItem(assistantConversationStorageKey(userId, assistantId))
      const target =
        conversations.value.find((item) => item.id === restoredId) || conversations.value[0]
      if (target) await select(target.id, userId)
      else {
        activeId.value = ''
        messages.value = []
      }
    } finally {
      syncMessage.value = ''
    }
  }

  function createStreamingMessage(userId: string) {
    return reactive<ChatMessage>({
      id: `temp-${Date.now()}`,
      conversation_id: activeId.value,
      user_id: userId,
      role: 'assistant',
      content: '',
      tool_events: [],
      timeline: [],
      status: 'streaming',
    })
  }

  function createOptimisticEditedMessage(userId: string, messageId: string, content: string) {
    const original = messages.value.find((message) => message.id === messageId)
    const temporaryId = `temp-user-${Date.now()}`
    const versionIds = original?.version_ids?.length
      ? original.version_ids
      : original
        ? [original.id]
        : []
    const siblingCount = original?.sibling_count || 1
    return reactive<ChatMessage>({
      ...(original || {
        conversation_id: activeId.value,
        user_id: userId,
        role: 'user' as const,
        parent_id: null,
      }),
      id: temporaryId,
      conversation_id: activeId.value,
      user_id: userId,
      role: 'user',
      content,
      reasoning_summary: null,
      tool_events: [],
      timeline: [],
      status: 'complete',
      sibling_count: siblingCount + 1,
      sibling_index: siblingCount,
      version_ids: [...versionIds, temporaryId],
    })
  }

  function appendStreamingMessage(userId: string) {
    const temporary = createStreamingMessage(userId)
    messages.value.push(temporary)
    return temporary
  }

  function replaceMessageId(message: ChatMessage, messageId: string) {
    const previousId = message.id
    message.id = messageId
    if (message.version_ids?.length)
      message.version_ids = message.version_ids.map((id) => (id === previousId ? messageId : id))
  }

  function updateConversationFromStream(event: { data: Record<string, string> }) {
    const conversationId = event.data.conversation_id || activeId.value
    const index = conversations.value.findIndex(
      (conversation) => conversation.id === conversationId,
    )
    const current = conversations.value[index]
    if (index === -1 || !current) return
    conversations.value[index] = {
      ...current,
      title: event.data.conversation_title || current.title,
      updated_at: event.data.conversation_updated_at || current.updated_at,
      last_message_at: event.data.conversation_last_message_at || current.last_message_at,
      active_message_id: event.data.conversation_active_message_id || current.active_message_id,
    }
  }

  function consumeStreamEvent(
    temporary: ChatMessage,
    event: { event: string; data: Record<string, string> },
  ) {
    if (event.event === 'message_start' && event.data.message_id) {
      replaceMessageId(temporary, event.data.message_id)
      temporary.parent_id = event.data.parent_message_id || temporary.parent_id
      if (event.data.created_at) temporary.created_at = event.data.created_at
      updateConversationFromStream(event)

      const temporaryIndex = messages.value.findIndex((message) => message === temporary)
      const parent = temporaryIndex > 0 ? messages.value[temporaryIndex - 1] : undefined
      if (
        parent?.role === 'user' &&
        event.data.parent_message_id &&
        (parent.id.startsWith('user-') || parent.id.startsWith('temp-user-'))
      ) {
        replaceMessageId(parent, event.data.parent_message_id)
        if (event.data.created_at) parent.created_at = event.data.created_at
      }
    }
    if (event.event === 'delta') {
      temporary.content += event.data.content || ''
      appendTimeline(temporary, { type: 'delta', content: event.data.content || '' })
    }
    if (event.event === 'reasoning_summary') {
      temporary.reasoning_summary = `${temporary.reasoning_summary || ''}${event.data.content || ''}`
      appendTimeline(temporary, { type: 'reasoning_summary', content: event.data.content || '' })
    }
    if (event.event === 'tool_started' || event.event === 'tool_finished') {
      temporary.tool_events.push(event.data)
      appendTimeline(temporary, {
        type: event.event,
        tool: event.data.tool || '工具',
        content: event.data.content,
      })
    }
    if (event.event === 'error') {
      temporary.status = 'error'
      error.value = event.data.message || '生成失败'
    }
    if (event.event === 'done') temporary.status = 'complete'
  }

  async function runGeneration(
    userId: string,
    start: (
      onEvent: (event: { event: string; data: Record<string, string> }) => void,
      signal: AbortSignal,
    ) => Promise<void>,
    placeTemporary: () => ChatMessage = () => appendStreamingMessage(userId),
  ) {
    const temporary = placeTemporary()
    generating.value = true
    error.value = ''
    controller = new AbortController()
    try {
      await start((event) => consumeStreamEvent(temporary, event), controller.signal)
    } catch (err) {
      if ((err as Error).name !== 'AbortError')
        error.value = err instanceof Error ? err.message : '生成失败'
      temporary.status = 'error'
    } finally {
      generating.value = false
      controller = null
    }
  }

  async function send(userId: string, content: string, runtime: ChatRuntimeContext) {
    if (!content.trim() || generating.value) return
    currentUserId = userId
    if (!activeId.value) await create(userId)
    messages.value.push({
      id: `user-${Date.now()}`,
      conversation_id: activeId.value,
      user_id: userId,
      role: 'user',
      content,
      tool_events: [],
      status: 'complete',
    })
    await runGeneration(userId, (onEvent, signal) =>
      api.streamChat(
        {
          user_id: userId,
          conversation_id: activeId.value,
          content,
          ...preferences.value,
          ...runtime,
        },
        onEvent,
        signal,
      ),
    )
  }
  async function retry(userId: string, messageId: string, runtime: ChatRuntimeContext) {
    if (generating.value || !activeId.value) return
    if (!messages.value.some((message) => message.id === messageId)) {
      error.value = '未能定位要重试的消息，请刷新会话后重试'
      return
    }
    await runGeneration(
      userId,
      (onEvent, signal) =>
        api.streamRetry(
          {
            user_id: userId,
            conversation_id: activeId.value,
            message_id: messageId,
            ...preferences.value,
            ...runtime,
          },
          onEvent,
          signal,
        ),
      () => {
        const original = messages.value.find((message) => message.id === messageId)
        const temporary = createStreamingMessage(userId)
        if (original) {
          const versionIds = original.version_ids?.length ? original.version_ids : [original.id]
          const siblingCount = original.sibling_count || 1
          temporary.sibling_count = siblingCount + 1
          temporary.sibling_index = siblingCount
          temporary.version_ids = [...versionIds, temporary.id]
        }
        messages.value = replaceTimelineBranch(messages.value, messageId, [temporary])
        return temporary
      },
    )
  }
  async function edit(
    userId: string,
    messageId: string,
    content: string,
    runtime: ChatRuntimeContext,
  ) {
    if (generating.value || !activeId.value || !content.trim()) return
    if (!messages.value.some((message) => message.id === messageId)) {
      error.value = '未能定位要编辑的消息，请刷新会话后重试'
      return
    }
    await runGeneration(
      userId,
      (onEvent, signal) =>
        api.streamEdit(
          {
            user_id: userId,
            conversation_id: activeId.value,
            message_id: messageId,
            content,
            ...preferences.value,
            ...runtime,
          },
          onEvent,
          signal,
        ),
      () => {
        const editedUser = createOptimisticEditedMessage(userId, messageId, content)
        const temporary = createStreamingMessage(userId)
        messages.value = replaceTimelineBranch(messages.value, messageId, [editedUser, temporary])
        return temporary
      },
    )
  }
  async function selectVersion(userId: string, messageId: string) {
    if (!activeId.value) return
    syncMessage.value = '正在切换消息版本…'
    try {
      await nextTick()
      const updated = await api.setActiveMessage(activeId.value, userId, messageId)
      const index = conversations.value.findIndex((item) => item.id === updated.id)
      if (index !== -1) conversations.value[index] = updated
      await select(activeId.value, userId)
    } finally {
      syncMessage.value = ''
    }
  }
  async function branch(userId: string, messageId: string) {
    if (!activeId.value) return
    syncMessage.value = '正在创建分支会话…'
    try {
      await nextTick()
      const conversation = await api.createBranch(activeId.value, userId, messageId)
      conversations.value.unshift(conversation)
      await select(conversation.id, userId)
    } finally {
      syncMessage.value = ''
    }
  }
  function stop() {
    controller?.abort()
  }
  async function remove(id: string, userId: string) {
    await api.deleteConversation(id, userId)
    conversations.value = conversations.value.filter((item) => item.id !== id)
    if (activeId.value === id) {
      activeId.value = ''
      messages.value = []
      clearActiveConversation(userId)
      if (conversations.value[0]) await select(conversations.value[0].id, userId)
    }
  }
  return {
    conversations,
    assistants,
    activeAssistantId,
    activeAssistant,
    messages,
    activeId,
    loading,
    generating,
    isSyncing,
    syncMessage,
    error,
    preferences,
    activeConversation,
    load,
    restorePreferences,
    persistPreferences,
    create,
    select,
    selectAssistant,
    rename,
    send,
    retry,
    edit,
    selectVersion,
    branch,
    stop,
    remove,
  }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useChatStore, import.meta.hot))
}
