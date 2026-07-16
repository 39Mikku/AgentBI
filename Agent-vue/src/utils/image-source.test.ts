import { afterEach, describe, expect, it, vi } from 'vitest'

import { generatedImageToDataUrl, prepareImageFile, validateImageFile } from './image-source'

afterEach(() => vi.unstubAllGlobals())

describe('image source utilities', () => {
  it('keeps small images unchanged without invoking compression', async () => {
    const file = new File(['small'], 'small.jpg', { type: 'image/jpeg' })
    const compress = vi.fn()

    const prepared = await prepareImageFile(file, {
      inspect: async () => ({ width: 1200, height: 800 }),
      compress,
    })

    expect(prepared).toBe(file)
    expect(compress).not.toHaveBeenCalled()
  })

  it('compresses images above 2 MiB and forwards the quality policy', async () => {
    const file = new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'large.jpg', {
      type: 'image/jpeg',
    })
    const compressed = new File(['compressed'], 'large.webp', { type: 'image/webp' })
    const compress = vi.fn().mockResolvedValue(compressed)

    const prepared = await prepareImageFile(file, {
      inspect: async () => ({ width: 3000, height: 2000 }),
      compress,
    })

    expect(prepared).toBe(compressed)
    expect(compress).toHaveBeenCalledWith(
      file,
      expect.objectContaining({ targetBytes: 2 * 1024 * 1024, maxDimension: 2560, quality: 0.88 }),
    )
  })

  it('skips GIF recompression and never replaces an image with a larger result', async () => {
    const gif = new File([new Uint8Array(3 * 1024 * 1024)], 'animated.gif', { type: 'image/gif' })
    const inspect = vi.fn()
    expect(await prepareImageFile(gif, { inspect })).toBe(gif)
    expect(inspect).not.toHaveBeenCalled()

    const png = new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'sheet.png', { type: 'image/png' })
    const larger = new File([new Uint8Array(3 * 1024 * 1024)], 'sheet.png', { type: 'image/png' })
    expect(
      await prepareImageFile(png, {
        inspect: async () => ({ width: 3000, height: 3000 }),
        compress: async () => larger,
      }),
    ).toBe(png)
  })

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
