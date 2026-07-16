import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  connectCodexImage,
  disconnectCodexImage,
  generateImage,
  getCodexImageStatus,
} from './image-generation'

afterEach(() => vi.unstubAllGlobals())

describe('image generation API', () => {
  it('sends direct prompts verbatim with the persisted provider selection', async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'image-1',
          url: '/api/generated-images/hash/direct/image-1.png',
          mode: 'lite',
          model: 'gemini-image',
          aspect_ratio: 'square',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', fetch)

    await generateImage({
      user_id: 'elysia@example.com',
      prompt: '原样发送，不要改写',
      aspect_ratio: 'square',
      provider_id: 'provider-1',
      scope_id: 'assistant-avatar',
    })

    const call = fetch.mock.calls[0]
    expect(call).toBeDefined()
    const init = call?.[1] as RequestInit
    expect(JSON.parse(String(init.body))).toEqual({
      user_id: 'elysia@example.com',
      prompt: '原样发送，不要改写',
      aspect_ratio: 'square',
      provider_id: 'provider-1',
      scope_id: 'assistant-avatar',
    })
  })

  it('uses token-free device login status endpoints', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ connected: false, pending: false, error: null }), {
          status: 200,
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            authorization_url: 'https://auth.openai.com/codex/device',
            user_code: 'ABCD-EFGH',
            expires_in: 900,
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)

    const status = await getCodexImageStatus()
    const login = await connectCodexImage()
    await disconnectCodexImage()

    expect(status.connected).toBe(false)
    expect(login.user_code).toBe('ABCD-EFGH')
    expect(JSON.stringify({ status, login })).not.toContain('access_token')
  })
})
