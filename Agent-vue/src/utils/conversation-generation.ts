export class ConversationGenerationTracker {
  private readonly active = new Set<string>()

  start(conversationId: string) {
    if (conversationId) this.active.add(conversationId)
  }

  finish(conversationId: string) {
    this.active.delete(conversationId)
  }

  has(conversationId: string) {
    return this.active.has(conversationId)
  }

  ids() {
    return [...this.active]
  }
}

export function hasGeneratingConversation(ids: readonly string[], conversationId: string) {
  return Boolean(conversationId) && ids.includes(conversationId)
}
