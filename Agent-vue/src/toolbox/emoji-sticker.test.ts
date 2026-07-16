import { describe, expect, it } from 'vitest'

import {
  buildStickerPrompt,
  detectStickerBounds,
  safeStickerFilename,
} from './emoji-sticker'

function pixels(width: number, height: number) {
  const data = new Uint8ClampedArray(width * height * 4)
  for (let index = 0; index < width * height; index += 1) {
    data[index * 4] = 250
    data[index * 4 + 1] = 248
    data[index * 4 + 2] = 245
    data[index * 4 + 3] = 255
  }
  return data
}

function paint(data: Uint8ClampedArray, width: number, x: number, y: number, w: number, h: number) {
  for (let py = y; py < y + h; py += 1) {
    for (let px = x; px < x + w; px += 1) {
      const offset = (py * width + px) * 4
      data[offset] = 30
      data[offset + 1] = 40
      data[offset + 2] = 50
      data[offset + 3] = 255
    }
  }
}

describe('emoji sticker pipeline', () => {
  it('builds a 4x4 sheet prompt and maps the text switch explicitly', () => {
    const withText = buildStickerPrompt({
      subject: '粉色长发少女的日常反应',
      style: '复古像素游戏头像',
      includeText: true,
    })
    const withoutText = buildStickerPrompt({
      subject: '粉色长发少女的日常反应',
      style: '复古像素游戏头像',
      includeText: false,
    })

    expect(withText).toContain('4×4')
    expect(withText).toContain('复古像素游戏头像')
    expect(withText).toContain('每张贴纸配简短中文文字')
    expect(withoutText).toContain('禁止出现任何文字')
    expect(withoutText).not.toContain('每张贴纸配简短中文文字')
  })

  it('detects separated foreground components against the corner-sampled background', () => {
    const width = 14
    const height = 8
    const data = pixels(width, height)
    paint(data, width, 2, 2, 3, 3)
    paint(data, width, 9, 1, 3, 4)

    const bounds = detectStickerBounds(
      { data, width, height },
      { backgroundTolerance: 20, minArea: 2, mergeGap: 0 },
    )

    expect(bounds).toEqual([
      { x: 9, y: 1, width: 3, height: 4 },
      { x: 2, y: 2, width: 3, height: 3 },
    ])
  })

  it('merges nearby fragments that belong to one sticker', () => {
    const width = 10
    const height = 8
    const data = pixels(width, height)
    paint(data, width, 2, 1, 3, 2)
    paint(data, width, 2, 4, 3, 2)

    const bounds = detectStickerBounds(
      { data, width, height },
      { backgroundTolerance: 20, minArea: 2, mergeGap: 1 },
    )

    expect(bounds).toEqual([{ x: 2, y: 1, width: 3, height: 5 }])
  })

  it('creates safe Chinese filenames with stable fallbacks', () => {
    expect(safeStickerFilename('开心挥手！', 0)).toBe('开心挥手.png')
    expect(safeStickerFilename('../', 1)).toBe('表情02.png')
  })
})
