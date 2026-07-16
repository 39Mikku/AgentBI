import DOMPurify from 'dompurify'
import { marked } from 'marked'

function suppressCardImages(source: string, suppressedImageUrls: readonly string[]): string {
  if (!suppressedImageUrls.length) return source
  const suppressed = new Set(suppressedImageUrls)
  return source.replace(/!\[[^\]]*\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g, (match, url) =>
    suppressed.has(url) ? '' : match,
  )
}

/** Render model Markdown while stripping unsafe HTML before it reaches v-html. */
export function renderMarkdown(source: string, suppressedImageUrls: readonly string[] = []): string {
  // Raw model HTML is always rendered as text; Markdown itself creates the allowed tags.
  const safeSource = suppressCardImages(source || '', suppressedImageUrls)
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
  const html = marked.parse(safeSource, { async: false, breaks: true, gfm: true })
  if (typeof DOMPurify.sanitize === 'function') {
    return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
  }
  // DOMPurify needs a browser DOM. This branch only supports the Node regression test.
  return html.replace(/\s(?:href|src)=(['"]?)\s*(?:javascript|data):[^'"\s>]*\1/gi, '')
}
