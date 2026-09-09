import { it } from 'vitest'
import assert from 'node:assert/strict'
import { loadSettingsResources } from '../src/utils/settings-load.ts'

it('legacy regression assertions', async () => {

  const result = await loadSettingsResources(
    async () => [{ id: 'provider-1' }],
    async () => {
      throw new Error('Not Found')
    },
  )

  assert.deepEqual(result.providers, [{ id: 'provider-1' }])
  assert.deepEqual(result.routes, [])
  assert.equal(result.providerError, '')
  assert.equal(result.routeError, '后台模型路由加载失败：Not Found')

})
