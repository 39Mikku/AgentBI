import { afterEach, describe, expect, it, vi } from 'vitest'

import { nameStickers } from './toolbox-emoji'

afterEach(() => vi.unstubAllGlobals())

describe('toolbox emoji API', () => {
  it('posts the selected naming strategy and image ids', async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          names: [{ id: 's1', name: '开心挥手' }],
          strategy: 'individual',
          model: 'vision-mini',
        }),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetch)

    await nameStickers({
      user_id: 'user-1',
      strategy: 'individual',
      images: [{ id: 's1', data_url: 'data:image/png;base64,aW1hZ2U=' }],
    })

    const body = JSON.parse(String(fetch.mock.calls[0]?.[1]?.body))
    expect(body.strategy).toBe('individual')
    expect(body.images[0].id).toBe('s1')
  })
})
