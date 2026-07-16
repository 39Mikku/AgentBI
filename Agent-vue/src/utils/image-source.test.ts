import { afterEach, describe, expect, it, vi } from 'vitest'

import { generatedImageToDataUrl, validateImageFile } from './image-source'

afterEach(() => vi.unstubAllGlobals())

describe('image source utilities', () => {
  it('rejects non-images and files above the configured limit', () => {
    expect(() => validateImageFile(new File(['text'], 'a.txt', { type: 'text/plain' }), 100)).toThrow(
      '图片',
    )
    expect(() =>
      validateImageFile(new File([new Uint8Array(101)], 'a.png', { type: 'image/png' }), 100),
    ).toThrow('100 B')
  })

  it('downloads generated media and converts it to a reusable data URL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(new Blob(['png'], { type: 'image/png' }), {
          status: 200,
          headers: { 'Content-Type': 'image/png' },
        }),
      ),
    )

    const value = await generatedImageToDataUrl('/api/generated-images/example.png')

    expect(value).toMatch(/^data:image\/png;base64,/)
  })
})
