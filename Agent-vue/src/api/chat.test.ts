import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPreferences, savePreferences } from './chat'

afterEach(() => vi.unstubAllGlobals())

describe('chat preference API', () => {
  it('maps the persisted Gemini thinking level in both directions', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: 'user-1',
            provider_id: 'provider-1',
            model: 'gemini-3.5-flash',
            temperature: 1,
            context_turns: 8,
            thinking_level: 'high',
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetch)

    const preferences = await getPreferences('user-1')
    expect(preferences.thinkingLevel).toBe('high')

    await savePreferences('user-1', preferences)
    expect(JSON.parse(String(fetch.mock.calls[1]?.[1]?.body)).thinking_level).toBe('high')
  })
})
