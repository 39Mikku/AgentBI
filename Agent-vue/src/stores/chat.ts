import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '@/api/chat'
import type { ChatMessage, ChatPreferences, Conversation } from '@/api/chat-types'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const activeId = ref('')
  const loading = ref(false)
  const generating = ref(false)
  const error = ref('')
  const preferences = ref<ChatPreferences>({ temperature: 0.7, contextTurns: 8 })
  let controller: AbortController | null = null
  const activeConversation = computed(() => conversations.value.find((item) => item.id === activeId.value) || null)

  async function load(userId: string) {
    loading.value = true
    try {
      conversations.value = await api.listConversations(userId)
      if (conversations.value[0] && !activeId.value) await select(conversations.value[0].id, userId)
    } catch (err) { error.value = err instanceof Error ? err.message : '加载会话失败' } finally { loading.value = false }
  }
  async function create(userId: string) {
    const conversation = await api.createConversation({ user_id: userId, title: '未命名会话', temperature: preferences.value.temperature, context_turns: preferences.value.contextTurns, provider_id: preferences.value.providerId, model: preferences.value.model })
    conversations.value.unshift(conversation); activeId.value = conversation.id; messages.value = []
  }
  async function select(id: string, userId: string) {
    activeId.value = id; messages.value = await api.listMessages(id, userId)
    const current = conversations.value.find((item) => item.id === id)
    if (current) preferences.value = { providerId: current.provider_id || undefined, model: current.model || undefined, temperature: current.temperature, contextTurns: current.context_turns }
  }
  async function send(userId: string, content: string) {
    if (!content.trim() || generating.value) return
    if (!activeId.value) await create(userId)
    const temporary: ChatMessage = { id: `temp-${Date.now()}`, conversation_id: activeId.value, user_id: userId, role: 'assistant', content: '', tool_events: [], status: 'streaming' }
    messages.value.push({ id: `user-${Date.now()}`, conversation_id: activeId.value, user_id: userId, role: 'user', content, tool_events: [], status: 'complete' }, temporary)
    generating.value = true; error.value = ''; controller = new AbortController()
    try {
      await api.streamChat({ user_id: userId, conversation_id: activeId.value, content, ...preferences.value }, (event) => {
        if (event.event === 'delta') temporary.content += event.data.content || ''
        if (event.event === 'reasoning_summary') temporary.reasoning_summary = `${temporary.reasoning_summary || ''}${event.data.content || ''}`
        if (event.event === 'tool_started' || event.event === 'tool_finished') temporary.tool_events.push(event.data)
        if (event.event === 'error') { temporary.status = 'error'; error.value = event.data.message || '生成失败' }
        if (event.event === 'done') temporary.status = 'complete'
      }, controller.signal)
      await load(userId)
      if (activeId.value) await select(activeId.value, userId)
    } catch (err) { if ((err as Error).name !== 'AbortError') error.value = err instanceof Error ? err.message : '生成失败'; temporary.status = 'error' } finally { generating.value = false; controller = null }
  }
  function stop() { controller?.abort() }
  async function remove(id: string, userId: string) { await api.deleteConversation(id, userId); conversations.value = conversations.value.filter((item) => item.id !== id); if (activeId.value === id) { activeId.value = ''; messages.value = []; if (conversations.value[0]) await select(conversations.value[0].id, userId) } }
  return { conversations, messages, activeId, loading, generating, error, preferences, activeConversation, load, create, select, send, stop, remove }
})
