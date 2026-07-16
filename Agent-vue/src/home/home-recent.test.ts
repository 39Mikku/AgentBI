import { describe, expect, it } from 'vitest'
import type { AssistantProfile, Conversation } from '@/api/chat-types'
import { mergeRecentConversations } from './home-recent'

const assistant = (id: string, name: string) => ({ id, name }) as AssistantProfile
const conversation = (
  id: string,
  assistantId: string,
  title: string,
  lastMessageAt: string,
) =>
  ({
    id,
    assistant_id: assistantId,
    title,
    last_message_at: lastMessageAt,
  }) as Conversation

describe('recent Studio conversations', () => {
  it('merges assistants, sorts by activity, and keeps three items', () => {
    const result = mergeRecentConversations(
      [assistant('a', '默认助手'), assistant('b', '写作助手')],
      [
        conversation('1', 'a', 'One', '2026-07-16T08:00:00'),
        conversation('2', 'b', 'Two', '2026-07-16T10:00:00'),
        conversation('3', 'a', 'Three', '2026-07-16T09:00:00'),
        conversation('4', 'b', 'Four', '2026-07-15T09:00:00'),
      ],
    )

    expect(result.map((item) => item.id)).toEqual(['2', '3', '1'])
    expect(result[0]?.assistantName).toBe('写作助手')
    expect(result[0]?.href).toBe('/chat?conversation=2')
  })

  it('falls back for missing titles, assistants, and timestamps', () => {
    const result = mergeRecentConversations(
      [],
      [{ id: 'space id', title: '', assistant_id: 'missing' } as Conversation],
    )

    expect(result[0]).toMatchObject({
      title: '未命名会话',
      assistantName: '',
      activityAt: '',
      href: '/chat?conversation=space%20id',
    })
  })
})
