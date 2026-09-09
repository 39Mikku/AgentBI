import { it } from 'vitest'
import assert from 'node:assert/strict'
import { shouldRefreshUserProfile } from '../src/utils/profile-refresh.ts'

it('legacy regression assertions', async () => {

  assert.equal(
    shouldRefreshUserProfile({ user_id: 'elysi@example.com', avatar_data_url: null }, 'elysi@example.com'),
    true,
  )
  assert.equal(
    shouldRefreshUserProfile({ user_id: 'elysi@example.com', avatar_data_url: 'data:image/png;base64,AA==' }, 'elysi@example.com'),
    false,
  )
  assert.equal(
    shouldRefreshUserProfile({ user_id: 'another@example.com', avatar_data_url: 'data:image/png;base64,AA==' }, 'elysi@example.com'),
    true,
  )

})
