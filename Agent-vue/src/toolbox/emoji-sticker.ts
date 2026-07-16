import JSZip from 'jszip'

export interface StickerPromptOptions {
  subject: string
  style: string
  includeText: boolean
  hasReference?: boolean
}

export interface StickerBounds {
  x: number
  y: number
  width: number
  height: number
}

export interface StickerCutOptions {
  backgroundTolerance: number
  minArea: number
  mergeGap: number
  padding: number
  strokeWidth: number
}

export interface PixelSource {
  data: Uint8ClampedArray
  width: number
  height: number
}

export interface CutSticker {
  id: string
  name: string
  dataUrl: string
  blob: Blob
  width: number
  height: number
}

export const DEFAULT_CUT_OPTIONS: StickerCutOptions = {
  backgroundTolerance: 30,
  minArea: 90,
  mergeGap: 16,
  padding: 14,
  strokeWidth: 6,
}

export function buildStickerPrompt(options: StickerPromptOptions) {
  const subject =
    options.subject.trim() ||
    (options.hasReference ? '参考图中的角色' : '一个适合日常聊天的原创角色')
  const textInstruction = options.includeText
    ? '每张贴纸配简短中文文字，文字必须清晰、自然并与情绪匹配。'
    : '禁止出现任何文字、字母、数字、字幕、气泡文案或水印。'
  return [
    `为“${subject}”设计一整张 4×4 表情贴纸表，共 16 个互不重复的表情。`,
    `统一风格：${options.style.trim()}。`,
    '每个贴纸都是完整独立的小构图，角色造型保持一致，包含明显不同的情绪、动作和反应。',
    textInstruction,
    '严格使用纯净接近白色的实心背景；贴纸之间保留宽阔且均匀的空白，不重叠、不越格、不裁切。',
    '输出为一张正方形完整贴纸表，不要额外标题、边框、页码或说明文字。',
  ].join('\n')
}

function sampleBackground(source: PixelSource) {
  const { data, width, height } = source
  const size = Math.max(1, Math.min(4, Math.floor(Math.min(width, height) / 4)))
  const samples: Array<[number, number, number]> = []
  const corners: Array<[number, number]> = [
    [0, 0],
    [Math.max(0, width - size), 0],
    [0, Math.max(0, height - size)],
    [Math.max(0, width - size), Math.max(0, height - size)],
  ]
  for (const [startX, startY] of corners) {
    for (let y = startY; y < startY + size; y += 1) {
      for (let x = startX; x < startX + size; x += 1) {
        const offset = (y * width + x) * 4
        if ((data[offset + 3] ?? 0) > 20) {
          samples.push([data[offset] ?? 0, data[offset + 1] ?? 0, data[offset + 2] ?? 0])
        }
      }
    }
  }
  const count = Math.max(1, samples.length)
  return samples.reduce<[number, number, number]>(
    (sum, color) => [sum[0] + color[0] / count, sum[1] + color[1] / count, sum[2] + color[2] / count],
    [0, 0, 0],
  )
}

function isForeground(
  source: PixelSource,
  index: number,
  background: [number, number, number],
  tolerance: number,
) {
  const offset = index * 4
  if ((source.data[offset + 3] ?? 0) < 20) return false
  const dr = (source.data[offset] ?? 0) - background[0]
  const dg = (source.data[offset + 1] ?? 0) - background[1]
  const db = (source.data[offset + 2] ?? 0) - background[2]
  return Math.sqrt(dr * dr + dg * dg + db * db) > tolerance
}

function shouldMerge(a: StickerBounds, b: StickerBounds, gap: number) {
  const dx = Math.max(a.x - (b.x + b.width), b.x - (a.x + a.width), 0)
  const dy = Math.max(a.y - (b.y + b.height), b.y - (a.y + a.height), 0)
  return dx <= gap && dy <= gap
}

function union(a: StickerBounds, b: StickerBounds): StickerBounds {
  const x = Math.min(a.x, b.x)
  const y = Math.min(a.y, b.y)
  const right = Math.max(a.x + a.width, b.x + b.width)
  const bottom = Math.max(a.y + a.height, b.y + b.height)
  return { x, y, width: right - x, height: bottom - y }
}

function mergeBounds(bounds: StickerBounds[], gap: number) {
  const merged = [...bounds]
  let changed = true
  while (changed) {
    changed = false
    outer: for (let left = 0; left < merged.length; left += 1) {
      for (let right = left + 1; right < merged.length; right += 1) {
        const leftBound = merged[left]
        const rightBound = merged[right]
        if (!leftBound || !rightBound || !shouldMerge(leftBound, rightBound, gap)) continue
        merged[left] = union(leftBound, rightBound)
        merged.splice(right, 1)
        changed = true
        break outer
      }
    }
  }
  return merged
}

export function detectStickerBounds(
  source: PixelSource,
  options: Partial<StickerCutOptions> = {},
): StickerBounds[] {
  const settings = { ...DEFAULT_CUT_OPTIONS, ...options }
  const { width, height } = source
  const background = sampleBackground(source)
  const visited = new Uint8Array(width * height)
  const components: StickerBounds[] = []
  for (let start = 0; start < visited.length; start += 1) {
    if (visited[start] || !isForeground(source, start, background, settings.backgroundTolerance)) continue
    const stack = [start]
    visited[start] = 1
    let area = 0
    let minX = width
    let minY = height
    let maxX = 0
    let maxY = 0
    while (stack.length) {
      const index = stack.pop() as number
      const x = index % width
      const y = Math.floor(index / width)
      area += 1
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
      const neighbors = [index - 1, index + 1, index - width, index + width]
      for (const neighbor of neighbors) {
        if (neighbor < 0 || neighbor >= visited.length || visited[neighbor]) continue
        const nx = neighbor % width
        const ny = Math.floor(neighbor / width)
        if (Math.abs(nx - x) + Math.abs(ny - y) !== 1) continue
        visited[neighbor] = 1
        if (isForeground(source, neighbor, background, settings.backgroundTolerance)) stack.push(neighbor)
      }
    }
    if (area >= settings.minArea) {
      components.push({ x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1 })
    }
  }
  return mergeBounds(components, settings.mergeGap).sort((a, b) => a.y - b.y || a.x - b.x)
}

function canvasBlob(canvas: HTMLCanvasElement) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('贴纸 PNG 导出失败'))), 'image/png')
  })
}

function loadImage(source: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('贴纸表读取失败'))
    image.src = source
  })
}

export async function cutStickerSheet(
  sourceUrl: string,
  options: Partial<StickerCutOptions> = {},
): Promise<CutSticker[]> {
  const settings = { ...DEFAULT_CUT_OPTIONS, ...options }
  const image = await loadImage(sourceUrl)
  const sheet = document.createElement('canvas')
  sheet.width = image.naturalWidth
  sheet.height = image.naturalHeight
  const sheetContext = sheet.getContext('2d', { willReadFrequently: true })
  if (!sheetContext) throw new Error('浏览器 Canvas 不可用')
  sheetContext.drawImage(image, 0, 0)
  const imageData = sheetContext.getImageData(0, 0, sheet.width, sheet.height)
  const background = sampleBackground(imageData)
  const bounds = detectStickerBounds(imageData, settings).slice(0, 24)
  const stickers: CutSticker[] = []
  for (const [index, bound] of bounds.entries()) {
    const raw = document.createElement('canvas')
    raw.width = bound.width
    raw.height = bound.height
    const rawContext = raw.getContext('2d', { willReadFrequently: true })
    if (!rawContext) continue
    rawContext.drawImage(
      sheet,
      bound.x,
      bound.y,
      bound.width,
      bound.height,
      0,
      0,
      bound.width,
      bound.height,
    )
    const pixels = rawContext.getImageData(0, 0, raw.width, raw.height)
    for (let pixel = 0; pixel < pixels.data.length; pixel += 4) {
      const dr = (pixels.data[pixel] ?? 0) - background[0]
      const dg = (pixels.data[pixel + 1] ?? 0) - background[1]
      const db = (pixels.data[pixel + 2] ?? 0) - background[2]
      if (Math.sqrt(dr * dr + dg * dg + db * db) <= settings.backgroundTolerance) {
        pixels.data[pixel + 3] = 0
      }
    }
    rawContext.putImageData(pixels, 0, 0)

    const output = document.createElement('canvas')
    const inset = settings.padding + settings.strokeWidth
    output.width = raw.width + inset * 2
    output.height = raw.height + inset * 2
    const outputContext = output.getContext('2d')
    if (!outputContext) continue
    if (settings.strokeWidth > 0) {
      const mask = document.createElement('canvas')
      mask.width = raw.width
      mask.height = raw.height
      const maskContext = mask.getContext('2d')
      if (maskContext) {
        maskContext.drawImage(raw, 0, 0)
        maskContext.globalCompositeOperation = 'source-in'
        maskContext.fillStyle = '#ffffff'
        maskContext.fillRect(0, 0, mask.width, mask.height)
        for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 12) {
          outputContext.drawImage(
            mask,
            inset + Math.cos(angle) * settings.strokeWidth,
            inset + Math.sin(angle) * settings.strokeWidth,
          )
        }
      }
    }
    outputContext.drawImage(raw, inset, inset)
    const blob = await canvasBlob(output)
    stickers.push({
      id: `sticker-${String(index + 1).padStart(2, '0')}`,
      name: `表情${String(index + 1).padStart(2, '0')}`,
      dataUrl: output.toDataURL('image/png'),
      blob,
      width: output.width,
      height: output.height,
    })
  }
  return stickers
}

export function safeStickerFilename(name: string, index: number) {
  const safe = name.trim().replace(/[^\p{L}\p{N}_-]+/gu, '').slice(0, 32)
  return `${safe || `表情${String(index + 1).padStart(2, '0')}`}.png`
}

export async function downloadStickerZip(stickers: CutSticker[], archiveName = 'emoji-stickers.zip') {
  const zip = new JSZip()
  stickers.forEach((sticker, index) => zip.file(safeStickerFilename(sticker.name, index), sticker.blob))
  const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = archiveName
  link.click()
  URL.revokeObjectURL(url)
}
