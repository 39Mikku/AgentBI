export async function copyMarkdown(text: string): Promise<void> {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
    await navigator.clipboard.writeText(text)
  } catch (error) {
    throw new Error('复制失败，请检查浏览器剪贴板权限', { cause: error })
  }
}
