import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  deletePlaygroundProfile,
  deletePlaygroundConversation,
  getPlaygroundPreferences,
  listPlaygroundConversations,
  savePlaygroundPreferences,
} from './playground'


describe('playground api', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('rejects failed deletes and accepts empty successful deletes', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: '删除失败' }), { status: 500 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 })))
    await expect(deletePlaygroundProfile('p', 'u')).rejects.toThrow('删除失败')
    await expect(deletePlaygroundConversation('c', 'u')).resolves.toBeUndefined()
  })

  it('keeps preferences separate and scopes conversation queries by profile', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: 'u',
            provider_id: 'p',
            model: 'm',
            temperature: 1,
            context_turns: 24,
            thinking_level: 'high',
            summary_provider_id: null,
            summary_model: null,
            summary_trigger_messages: 24,
            summary_retain_messages: 8,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response('[]', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const preferences = await getPlaygroundPreferences('u')
    await listPlaygroundConversations('u', 'character-1', 'character')

    expect(preferences.providerId).toBe('p')
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/api/playground/preferences')
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('profile_id=character-1')
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('profile_type=character')
  })

  it('maps camel case preference state back to the strict backend contract', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: 'u',
          provider_id: 'p',
          model: 'm',
          temperature: 1,
          context_turns: 0,
          thinking_level: 'medium',
          summary_provider_id: 'p',
          summary_model: 'summary',
          summary_trigger_messages: 30,
          summary_retain_messages: 10,
        }),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await savePlaygroundPreferences('u', {
      providerId: 'p',
      model: 'm',
      temperature: 1,
      contextTurns: 0,
      thinkingLevel: 'medium',
      summaryProviderId: 'p',
      summaryModel: 'summary',
      summaryTriggerMessages: 30,
      summaryRetainMessages: 10,
    })

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))
    expect(body).toEqual({
      provider_id: 'p',
      model: 'm',
      temperature: 1,
      context_turns: 0,
      thinking_level: 'medium',
      summary_provider_id: 'p',
      summary_model: 'summary',
      summary_trigger_messages: 30,
      summary_retain_messages: 10,
    })
  })
})
