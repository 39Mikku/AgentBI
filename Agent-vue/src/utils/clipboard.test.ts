import { afterEach, describe, expect, it, vi } from 'vitest'
import { copyMarkdown } from './clipboard'

afterEach(() => vi.unstubAllGlobals())

describe('copyMarkdown', () => {
  it('copies raw markdown unchanged', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })

    await copyMarkdown('# 标题\n\n**正文**')

    expect(writeText).toHaveBeenCalledWith('# 标题\n\n**正文**')
  })

  it('surfaces clipboard errors', async () => {
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    await expect(copyMarkdown('text')).rejects.toThrow('复制失败')
  })
})
