import { it } from 'vitest'
import assert from 'node:assert/strict'
import { toTimelineCard } from '../src/utils/card-events.ts'

it('legacy regression assertions', async () => {

  assert.deepEqual(
    toTimelineCard({
      kind: 'music.track',
      payload: { tracks: [{ id: '1', name: 'Song' }] },
    }),
    {
      type: 'card',
      kind: 'music.track',
      payload: { tracks: [{ id: '1', name: 'Song' }] },
    },
  )

  assert.equal(toTimelineCard({ kind: 'future.card', payload: 'invalid' }), null)
  assert.equal(toTimelineCard({ payload: {} }), null)

})
