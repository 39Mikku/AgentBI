import { it } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  bilibiliVideoUrl,
  buildBilibiliPlayerUrl,
  isValidBvid,
} from '../src/utils/bilibili-player.ts'

it('legacy regression assertions', async () => {

  assert.equal(isValidBvid('BV1xx411c7mD'), true)
  assert.equal(isValidBvid('not-a-bvid'), false)
  assert.equal(bilibiliVideoUrl('BV1xx411c7mD'), 'https://www.bilibili.com/video/BV1xx411c7mD')
  assert.equal(
    buildBilibiliPlayerUrl('BV1xx411c7mD'),
    'https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&page=1&high_quality=1&danmaku=0&autoplay=0',
  )
  assert.match(buildBilibiliPlayerUrl('BV1xx411c7mD', 2), /page=2/)
  assert.throws(() => buildBilibiliPlayerUrl('javascript:alert(1)'), /BV/)

  const videoCardSource = readFileSync(
    new URL('../src/components/cards/BilibiliVideoCard.vue', import.meta.url),
    'utf8',
  )
  assert.match(videoCardSource, /referrerpolicy="no-referrer"/)

})
