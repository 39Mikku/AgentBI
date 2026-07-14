import type { ChatRuntimeContext } from '../api/chat-types'

export function createRuntimeContext(userName: string, locale?: string, timezone?: string): ChatRuntimeContext {
  return {
    userName: userName.trim() || '用户',
    locale: locale || 'zh-CN',
    timezone: timezone || 'Asia/Shanghai',
  }
}
