import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('suppresses an image already rendered by a timeline card', () => {
    const url = '/api/generated-images/user/thread/image.png'
    const html = renderMarkdown(`完成\n\n![生成图](${url})\n\n请查看卡片。`, [url])

    expect(html).not.toContain('<img')
    expect(html).toContain('完成')
    expect(html).toContain('请查看卡片')
  })

  it('keeps unrelated markdown images', () => {
    const html = renderMarkdown('![参考图](https://example.com/reference.png)', [
      '/api/generated-images/image.png',
    ])

    expect(html).toContain('<img')
    expect(html).toContain('https://example.com/reference.png')
  })
})
