type FileLike = Pick<File, 'name' | 'size' | 'type'>

const MB = 1024 * 1024
const DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif'])

export function validateAttachmentBatch(files: FileLike[]): string {
  if (files.length > 8) return '单条消息最多添加 8 个附件'
  if (files.reduce((total, file) => total + file.size, 0) > 30 * MB)
    return '附件总大小不能超过 30 MB'
  for (const file of files) {
    const lower = file.name.toLowerCase()
    const isImage = IMAGE_TYPES.has(file.type) && /\.(png|jpe?g|webp|gif)$/.test(lower)
    const isDocx = file.type === DOCX_MIME && lower.endsWith('.docx')
    if (!isImage && !isDocx) return '仅支持 PNG、JPG、WebP、GIF 和 DOCX'
    if (isImage && file.size > 10 * MB) return `${file.name} 超过图片 10 MB 限制`
    if (isDocx && file.size > 20 * MB) return `${file.name} 超过 DOCX 20 MB 限制`
  }
  return ''
}

export function formatAssetSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < MB) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / MB).toFixed(1)} MB`
}

export function assetContentUrl(assetId: string, userId: string): string {
  return `/api/assets/${encodeURIComponent(assetId)}/content?user_id=${encodeURIComponent(userId)}`
}
