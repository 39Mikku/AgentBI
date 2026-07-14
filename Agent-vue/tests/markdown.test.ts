import assert from 'node:assert/strict'

import { renderMarkdown } from '../src/utils/markdown'

const rendered = renderMarkdown('## 标题\n\n**加粗** 与 `代码`\n\n- 第一项\n- 第二项\n\n[站点](https://example.com)')

assert.match(rendered, /<h2>标题<\/h2>/)
assert.match(rendered, /<strong>加粗<\/strong>/)
assert.match(rendered, /<code>代码<\/code>/)
assert.match(rendered, /<ul>/)
assert.match(rendered, /href="https:\/\/example\.com"/)
assert.doesNotMatch(renderMarkdown('<script>alert(1)</script>'), /<script>/)
