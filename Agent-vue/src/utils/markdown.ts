import DOMPurify from 'dompurify'
import { marked } from 'marked'

/** Render model Markdown while stripping unsafe HTML before it reaches v-html. */
export function renderMarkdown(source: string): string {
  // Raw model HTML is always rendered as text; Markdown itself creates the allowed tags.
  const safeSource = (source || '').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  const html = marked.parse(safeSource, { async: false, breaks: true, gfm: true })
  if (typeof DOMPurify.sanitize === 'function') {
    return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
  }
  // DOMPurify needs a browser DOM. This branch only supports the Node regression test.
  return html.replace(/\s(?:href|src)=(['"]?)\s*(?:javascript|data):[^'"\s>]*\1/gi, '')
}
