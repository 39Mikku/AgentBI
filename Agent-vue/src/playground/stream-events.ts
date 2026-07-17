import type { PlaygroundMessage, PlaygroundStreamEvent } from '@/api/playground-types'


export function applyPlaygroundStreamEvent(
  message: PlaygroundMessage,
  event: PlaygroundStreamEvent,
) {
  if (event.event === 'message_start' && event.data.message_id) {
    const previousId = message.id
    message.id = String(event.data.message_id)
    message.parent_id = event.data.parent_message_id || message.parent_id
    message.created_at = event.data.created_at || message.created_at
    if (message.version_ids?.length) {
      message.version_ids = message.version_ids.map((id) =>
        id === previousId ? message.id : id,
      )
    }
  } else if (event.event === 'delta') {
    const content = String(event.data.content || '')
    message.content += content
    appendTimeline(message, 'delta', content)
  } else if (event.event === 'reasoning_summary') {
    const content = String(event.data.content || '')
    message.reasoning_summary = `${message.reasoning_summary || ''}${content}`
    appendTimeline(message, 'reasoning_summary', content)
  } else if (event.event === 'state_snapshot') {
    message.metadata.state_snapshot = event.data.snapshot || null
  } else if (event.event === 'action_options') {
    message.metadata.action_options = Array.isArray(event.data.options)
      ? event.data.options
      : []
  } else if (event.event === 'done') {
    message.status = 'complete'
  } else if (event.event === 'error') {
    message.status = 'error'
  }
  return message
}


function appendTimeline(
  message: PlaygroundMessage,
  type: 'delta' | 'reasoning_summary',
  content: string,
) {
  message.timeline ||= []
  const previous = message.timeline.at(-1)
  if (previous?.type === type) previous.content = `${previous.content || ''}${content}`
  else message.timeline.push({ type, content })
}


export async function consumePlaygroundSse(
  response: Response,
  onEvent: (event: PlaygroundStreamEvent) => void,
) {
  if (!response.body) throw new Error('流式响应不可用')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() || ''
    for (const frame of frames) parseFrame(frame, onEvent)
    if (done) break
  }
  if (buffer.trim()) parseFrame(buffer, onEvent)
}


function parseFrame(
  frame: string,
  onEvent: (event: PlaygroundStreamEvent) => void,
) {
  const name = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim()
  const raw = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (!name || !raw) return
  onEvent({
    event: name as PlaygroundStreamEvent['event'],
    data: JSON.parse(raw) as Record<string, any>,
  })
}
