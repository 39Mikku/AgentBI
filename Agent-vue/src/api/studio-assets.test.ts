import { afterEach, describe, expect, it, vi } from 'vitest'
import { listAssets, uploadAsset } from './studio-assets'

afterEach(() => vi.unstubAllGlobals())

describe('studio assets API', () => {
  it('uploads multipart data and maps library filters', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'asset-1' }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    const file = new File(['image'], 'one.png', { type: 'image/png' })

    await uploadAsset('user@example.com', file)
    await listAssets('user@example.com', { kind: 'image', source: 'generated', search: 'cat' })

    expect(fetch.mock.calls[0]?.[1]?.body).toBeInstanceOf(FormData)
    expect(String(fetch.mock.calls[1]?.[0])).toContain('kind=image')
    expect(String(fetch.mock.calls[1]?.[0])).toContain('source=generated')
    expect(String(fetch.mock.calls[1]?.[0])).toContain('search=cat')
  })
})
