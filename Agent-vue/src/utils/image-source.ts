export function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

export function validateImageFile(file: File, maxBytes: number) {
  if (!file.type.startsWith('image/')) throw new Error('请选择图片文件')
  if (file.size > maxBytes) throw new Error(`图片请控制在 ${formatBytes(maxBytes)} 以内`)
}

export async function blobToDataUrl(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer())
  let binary = ''
  const chunk = 0x8000
  for (let offset = 0; offset < bytes.length; offset += chunk) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunk))
  }
  return `data:${blob.type || 'image/png'};base64,${btoa(binary)}`
}

export async function fileToDataUrl(file: File, maxBytes: number) {
  validateImageFile(file, maxBytes)
  return blobToDataUrl(file)
}

export async function generatedImageToDataUrl(url: string) {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`读取生成图片失败 (${response.status})`)
  const blob = await response.blob()
  if (!blob.type.startsWith('image/')) throw new Error('生成结果不是图片')
  return blobToDataUrl(blob)
}

