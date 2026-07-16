import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveModelCapability } from './model-capabilities'

afterEach(() => vi.unstubAllGlobals())

describe('model capability API', () => {
  it('binds vision support to the exact provider and model', async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: 'user-1',
          provider_id: 'provider-1',
          model: 'vision-model',
          supports_vision: true,
        }),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetch)

    await saveModelCapability('user-1', 'provider-1', 'vision-model', true)

    expect(JSON.parse(String(fetch.mock.calls[0]?.[1]?.body))).toEqual({
      provider_id: 'provider-1',
      model: 'vision-model',
      supports_vision: true,
    })
  })
})
