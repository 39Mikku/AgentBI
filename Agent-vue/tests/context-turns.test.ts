import { it } from 'vitest'
import assert from 'node:assert/strict'
import { contextTurnLabel, contextTurnSliderIndex, contextTurnsFromSlider, CONTEXT_TURN_STEPS } from '../src/utils/context-turns.ts'

it('legacy regression assertions', async () => {

  assert.deepEqual(CONTEXT_TURN_STEPS, [2, 4, 8, 16, 32, 64, 128, 0])
  assert.equal(contextTurnsFromSlider(3), 16)
  assert.equal(contextTurnSliderIndex(8), 2)
  assert.equal(contextTurnSliderIndex(30), 4)
  assert.equal(contextTurnLabel(0), String.fromCodePoint(0x4e0d, 0x622a, 0x65ad))

})
