import { describe, expect, it } from 'vitest'
import { validateAttachmentBatch } from './chat-attachments'

const mb = 1024 * 1024

describe('validateAttachmentBatch', () => {
  it('accepts supported images and docx within limits', () => {
    expect(
      validateAttachmentBatch([
        { name: 'one.png', size: 2 * mb, type: 'image/png' },
        {
          name: 'notes.docx',
          size: 3 * mb,
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        },
      ]),
    ).toBe('')
  })

  it('rejects unsupported and excessive batches', () => {
    expect(validateAttachmentBatch([{ name: 'report.pdf', size: 20, type: 'application/pdf' }])).toContain(
      'PNG',
    )
    expect(
      validateAttachmentBatch(
        Array.from({ length: 9 }, (_, index) => ({
          name: `${index}.png`,
          size: 1,
          type: 'image/png',
        })),
      ),
    ).toContain('8')
  })
})
