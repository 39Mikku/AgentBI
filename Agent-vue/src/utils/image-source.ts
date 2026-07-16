export function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

const MB = 1024 * 1024
export const DEFAULT_IMAGE_TARGET_BYTES = 2 * MB
export const DEFAULT_IMAGE_MAX_DIMENSION = 2560
export const DEFAULT_IMAGE_QUALITY = 0.88
const MAX_SOURCE_BYTES = 50 * MB

export interface ImageDimensions {
  width: number
  height: number
}

export interface ImageCompressionRequest {
  targetBytes: number
  maxDimension: number
  quality: number
  dimensions: ImageDimensions
}

export interface PrepareImageOptions {
  targetBytes?: number
  maxDimension?: number
  quality?: number
  inspect?: (file: File) => Promise<ImageDimensions>
  compress?: (file: File, request: ImageCompressionRequest) => Promise<File>
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

async function loadDrawable(file: File) {
  if (typeof createImageBitmap === 'function') {
    const bitmap = await createImageBitmap(file)
    return {
      source: bitmap as CanvasImageSource,
      width: bitmap.width,
      height: bitmap.height,
      close: () => bitmap.close(),
    }
  }
  const url = URL.createObjectURL(file)
  const image = new Image()
  image.src = url
  await image.decode()
  return {
    source: image as CanvasImageSource,
    width: image.naturalWidth,
    height: image.naturalHeight,
    close: () => URL.revokeObjectURL(url),
  }
}

async function inspectImage(file: File): Promise<ImageDimensions> {
  const drawable = await loadDrawable(file)
  try {
    return { width: drawable.width, height: drawable.height }
  } finally {
    drawable.close()
  }
}

function canvasBlob(canvas: HTMLCanvasElement, type: string, quality?: number) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('浏览器无法压缩这张图片'))),
      type,
      quality,
    )
  })
}

async function compressWithCanvas(file: File, request: ImageCompressionRequest): Promise<File> {
  const drawable = await loadDrawable(file)
  const outputType = file.type === 'image/png' ? 'image/png' : 'image/webp'
  let scale = Math.min(1, request.maxDimension / Math.max(drawable.width, drawable.height))
  let quality = request.quality
  let best: Blob | null = null
  try {
    for (let attempt = 0; attempt < 6; attempt += 1) {
      const width = Math.max(1, Math.round(drawable.width * scale))
      const height = Math.max(1, Math.round(drawable.height * scale))
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d', { alpha: outputType === 'image/png' })
      if (!context) throw new Error('浏览器 Canvas 不可用')
      context.imageSmoothingEnabled = true
      context.imageSmoothingQuality = 'high'
      context.drawImage(drawable.source, 0, 0, width, height)
      const blob = await canvasBlob(canvas, outputType, outputType === 'image/png' ? undefined : quality)
      if (!best || blob.size < best.size) best = blob
      if (blob.size <= request.targetBytes) break
      if (outputType !== 'image/png' && quality > 0.68) quality -= 0.08
      else scale *= Math.max(0.62, Math.min(0.88, Math.sqrt(request.targetBytes / blob.size) * 0.94))
    }
  } finally {
    drawable.close()
  }
  if (!best) return file
  const name = outputType === 'image/png' ? file.name : file.name.replace(/\.[^.]+$/, '') + '.webp'
  return new File([best], name, { type: outputType, lastModified: file.lastModified })
}

export async function prepareImageFile(
  file: File,
  options: PrepareImageOptions = {},
): Promise<File> {
  validateImageFile(file, MAX_SOURCE_BYTES)
  if (file.type === 'image/gif') return file
  const targetBytes = options.targetBytes ?? DEFAULT_IMAGE_TARGET_BYTES
  const maxDimension = options.maxDimension ?? DEFAULT_IMAGE_MAX_DIMENSION
  const quality = options.quality ?? DEFAULT_IMAGE_QUALITY
  const dimensions = await (options.inspect ?? inspectImage)(file)
  if (
    file.size <= targetBytes &&
    dimensions.width <= maxDimension &&
    dimensions.height <= maxDimension
  )
    return file
  const compressed = await (options.compress ?? compressWithCanvas)(file, {
    targetBytes,
    maxDimension,
    quality,
    dimensions,
  })
  return compressed.size < file.size ? compressed : file
}

export async function fileToDataUrl(file: File, maxBytes: number) {
  const prepared = await prepareImageFile(file, {
    targetBytes: Math.min(DEFAULT_IMAGE_TARGET_BYTES, maxBytes),
  })
  validateImageFile(prepared, maxBytes)
  return blobToDataUrl(prepared)
}

export async function generatedImageToDataUrl(url: string) {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`读取生成图片失败 (${response.status})`)
  const blob = await response.blob()
  if (!blob.type.startsWith('image/')) throw new Error('生成结果不是图片')
  return blobToDataUrl(blob)
}
