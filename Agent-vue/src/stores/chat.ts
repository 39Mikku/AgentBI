import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import * as api from '@/api/chat'
import type { ChatMessage, ChatPreferences, ChatRuntimeContext, ChatTimelineEvent, Conversation } from '@/api/chat-types'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const activeId = ref('')
  const loading = ref(false)
  const generating = ref(false)
  const error = ref('')
  const preferences = ref<ChatPreferences>({ temperature: 0.7, contextTurns: 8 })
  let controller: AbortController | null = null
  let currentUserId = ''
  let preferenceTimer: ReturnType<typeof setTimeout> | null = null
  const activeConversation = computed(() => conversations.value.find((item) => item.id === activeId.value) || null)

  function activeStorageKey(userId: string) { return `agentbi_active_conversation:${userId}` }
  function saveActiveConversation(userId: string, id: string) { localStorage.setItem(activeStorageKey(userId), id) }
  function clearActiveConversation(userId: string) { localStorage.removeItem(activeStorageKey(userId)) }

  async function restorePreferences(userId: string) {
    currentUserId = userId
    preferences.value = await api.getPreferences(userId)
  }

  async function persistPreferences() {
    if (currentUserId) await api.savePreferences(currentUserId, preferences.value)
  }

  watch(preferences, () => {
    if (!currentUserId) return
    if (preferenceTimer) clearTimeout(preferenceTimer)
    preferenceTimer = setTimeout(() => { void persistPreferences() }, 250)
  }, { deep: true })

  function appendTimeline(message: ChatMessage, event: ChatTimelineEvent) {
    message.timeline ||= []
    const previous = message.timeline.at(-1)
    if ((event.type === 'delta' || event.type === 'reasoning_summary') && previous?.type === event.type) {
      previous.content = `${previous.content || ''}${event.content || ''}`
    } else {
      message.timeline.push(event)
    }
  }

  async function load(userId: string) {
    loading.value = true
    try {
      await restorePreferences(userId)
      conversations.value = await api.listConversations(userId)
      const restoredId = localStorage.getItem(activeStorageKey(userId))
      const target = conversations.value.find((item) => item.id === restoredId) || conversations.value[0]
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
      }
      else { activeId.value = ''; messages.value = [] }
    } catch (err) { error.value = err instanceof Error ? err.message : '加载会话失败' } finally { loading.value = false }
  }
  async function create(userId: string) {
    currentUserId = userId
    const conversation = await api.createConversation({ user_id: userId, title: '未命名会话', temperature: preferences.value.temperature, context_turns: preferences.value.contextTurns, provider_id: preferences.value.providerId, model: preferences.value.model })
    conversations.value.unshift(conversation); activeId.value = conversation.id; messages.value = []; saveActiveConversation(userId, conversation.id)
  }
  async function select(id: string, userId: string) {
    currentUserId = userId; activeId.value = id; saveActiveConversation(userId, id); messages.value = await api.listMessages(id, userId)
  }
  async function rename(id: string, userId: string, title: string) {
    const normalized = title.trim()
    if (!normalized) return
    const updated = await api.updateConversation(id, userId, { title: normalized })
    const index = conversations.value.findIndex((item) => item.id === id)
    if (index !== -1) conversations.value[index] = updated
  }
  async function send(userId: string, content: string, runtime: ChatRuntimeContext) {
    if (!content.trim() || generating.value) return
    currentUserId = userId
    if (!activeId.value) await create(userId)
    const temporary = reactive<ChatMessage>({ id: `temp-${Date.now()}`, conversation_id: activeId.value, user_id: userId, role: 'assistant', content: '', tool_events: [], timeline: [], status: 'streaming' })
    messages.value.push({ id: `user-${Date.now()}`, conversation_id: activeId.value, user_id: userId, role: 'user', content, tool_events: [], status: 'complete' }, temporary)
    generating.value = true; error.value = ''; controller = new AbortController()
    try {
      await api.streamChat({ user_id: userId, conversation_id: activeId.value, content, ...preferences.value, ...runtime }, (event) => {
        if (event.event === 'delta') { temporary.content += event.data.content || ''; appendTimeline(temporary, { type: 'delta', content: event.data.content || '' }) }
        if (event.event === 'reasoning_summary') { temporary.reasoning_summary = `${temporary.reasoning_summary || ''}${event.data.content || ''}`; appendTimeline(temporary, { type: 'reasoning_summary', content: event.data.content || '' }) }
        if (event.event === 'tool_started' || event.event === 'tool_finished') { temporary.tool_events.push(event.data); appendTimeline(temporary, { type: event.event, tool: event.data.tool || '工具', content: event.data.content }) }
        if (event.event === 'error') { temporary.status = 'error'; error.value = event.data.message || '生成失败' }
        if (event.event === 'done') temporary.status = 'complete'
      }, controller.signal)
      await load(userId)
      if (activeId.value) await select(activeId.value, userId)
    } catch (err) { if ((err as Error).name !== 'AbortError') error.value = err instanceof Error ? err.message : '生成失败'; temporary.status = 'error' } finally { generating.value = false; controller = null }
  }
  function stop() { controller?.abort() }
  async function remove(id: string, userId: string) { await api.deleteConversation(id, userId); conversations.value = conversations.value.filter((item) => item.id !== id); if (activeId.value === id) { activeId.value = ''; messages.value = []; clearActiveConversation(userId); if (conversations.value[0]) await select(conversations.value[0].id, userId) } }
  return { conversations, messages, activeId, loading, generating, error, preferences, activeConversation, load, restorePreferences, persistPreferences, create, select, rename, send, stop, remove }
})
