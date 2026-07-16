import type { AssistantProfile, Conversation } from '@/api/chat-types'

export interface RecentConversation {
  id: string
  title: string
  assistantName: string
  activityAt: string
  href: string
}

function activityAt(conversation: Conversation): string {
  return conversation.last_message_at || conversation.updated_at || conversation.created_at || ''
}

export function mergeRecentConversations(
  assistants: AssistantProfile[],
  conversations: Conversation[],
  limit = 3,
): RecentConversation[] {
  const assistantNames = new Map(assistants.map((assistant) => [assistant.id, assistant.name]))

  return [...conversations]
    .sort((left, right) => {
      const leftTime = Date.parse(activityAt(left)) || 0
      const rightTime = Date.parse(activityAt(right)) || 0
      return rightTime - leftTime
    })
    .slice(0, Math.max(0, limit))
    .map((conversation) => ({
      id: conversation.id,
      title: conversation.title.trim() || '未命名会话',
      assistantName: conversation.assistant_id
        ? assistantNames.get(conversation.assistant_id) || ''
        : '',
      activityAt: activityAt(conversation),
      href: `/chat?conversation=${encodeURIComponent(conversation.id)}`,
    }))
}
