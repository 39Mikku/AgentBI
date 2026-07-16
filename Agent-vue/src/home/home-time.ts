const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

export function greetingForHour(hour: number): string {
  if (hour >= 5 && hour < 9) return '清晨好'
  if (hour >= 9 && hour < 12) return '上午好'
  if (hour >= 12 && hour < 18) return '下午好'
  if (hour >= 18 && hour < 24) return '晚上好'
  return '夜深了'
}

export function formatHomeDate(date: Date): string {
  const weekday = WEEKDAYS[date.getDay()] ?? ''
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 · ${weekday}`
}

export function formatRelativeTime(value: string | null | undefined, now = new Date()): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const difference = Math.max(0, now.getTime() - date.getTime())
  const minutes = Math.floor(difference / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  if (hours < 48) return '昨天'

  return `${date.getMonth() + 1}月${date.getDate()}日`
}
