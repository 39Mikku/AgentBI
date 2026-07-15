export type BilibiliVideo = {
  bvid: string
  title: string
  author: string
  cover_url?: string | null
  duration_seconds: number
  play_count: number
  published_at?: number | null
  description?: string
  url?: string
}

const BVID_PATTERN = /^BV[0-9A-Za-z]{10}$/

export function isValidBvid(value: string) {
  return BVID_PATTERN.test(value.trim())
}

function checkedBvid(value: string) {
  const bvid = value.trim()
  if (!isValidBvid(bvid)) throw new Error('无效的 BV 号')
  return bvid
}

export function bilibiliVideoUrl(bvid: string) {
  return `https://www.bilibili.com/video/${checkedBvid(bvid)}`
}

export function buildBilibiliPlayerUrl(bvid: string, page = 1) {
  const params = new URLSearchParams({
    bvid: checkedBvid(bvid),
    page: String(Math.max(1, Math.trunc(page) || 1)),
    high_quality: '1',
    danmaku: '0',
    autoplay: '0',
  })
  return `https://player.bilibili.com/player.html?${params.toString()}`
}
