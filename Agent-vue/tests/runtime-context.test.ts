import { it } from 'vitest'
import assert from 'node:assert/strict'
import { createRuntimeContext } from '../src/utils/runtime-context'

it('legacy regression assertions', async () => {

  assert.deepEqual(
    createRuntimeContext('Elysi', 'zh-CN', 'Asia/Shanghai'),
    { userName: 'Elysi', locale: 'zh-CN', timezone: 'Asia/Shanghai' },
  )

})
