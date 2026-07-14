/**
 * Replace the active timeline from an existing message onward.
 *
 * Retrying or editing creates a sibling branch on the server.  While that
 * branch is streaming, the UI should already show it at its real position
 * instead of appending a temporary assistant message to the end.
 */
export function replaceTimelineBranch<T extends { id: string }>(
  messages: T[],
  anchorMessageId: string,
  replacements: T[],
): T[] {
  const anchorIndex = messages.findIndex((message) => message.id === anchorMessageId)
  return anchorIndex === -1
    ? messages
    : [...messages.slice(0, anchorIndex), ...replacements]
}
