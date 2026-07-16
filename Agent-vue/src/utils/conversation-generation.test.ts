import { describe, expect, it } from 'vitest'
import { computed, ref } from 'vue'

import { ConversationGenerationTracker, hasGeneratingConversation } from './conversation-generation'

describe('ConversationGenerationTracker', () => {
  it('keeps generation attached to its source conversation across selection changes', () => {
    const tracker = new ConversationGenerationTracker()
    let activeConversationId = 'conversation-a'

    tracker.start(activeConversationId)
    activeConversationId = 'conversation-b'

    expect(tracker.has('conversation-a')).toBe(true)
    expect(tracker.has(activeConversationId)).toBe(false)
    tracker.finish('conversation-a')
    expect(tracker.ids()).toEqual([])
  })

  it('is idempotent for duplicate starts and terminal cleanup', () => {
    const tracker = new ConversationGenerationTracker()

    tracker.start('conversation-a')
    tracker.start('conversation-a')
    expect(tracker.ids()).toEqual(['conversation-a'])
    tracker.finish('conversation-a')
    tracker.finish('conversation-a')
    expect(tracker.ids()).toEqual([])
  })

  it('derives active state from a reactive id snapshot', () => {
    const ids = ref<string[]>([])
    const activeId = ref('conversation-a')
    const active = computed(() => hasGeneratingConversation(ids.value, activeId.value))

    expect(active.value).toBe(false)
    ids.value = ['conversation-a']
    expect(active.value).toBe(true)
    activeId.value = 'conversation-b'
    expect(active.value).toBe(false)
  })
})
