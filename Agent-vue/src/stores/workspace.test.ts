import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { useWorkspaceStore } from './workspace'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

it('waits for the backend identity before opening the workbench', async () => {
  const store = useWorkspaceStore()
  const profile = { user_id: 'old@example.com', username: '旧资料', email: 'old@example.com' }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ profile, profiles: [profile] }))))
  expect(store.ready).toBe(false)
  await store.initialize()
  expect(store.ready).toBe(true)
  expect(store.userId).toBe(profile.user_id)
})

it('keeps the selection screen for multiple legacy profiles', async () => {
  const profile = { user_id: 'old@example.com', username: '旧资料' }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ profile: null, profiles: [profile] })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ profile, profiles: [profile] })))
  vi.stubGlobal('fetch', fetchMock)
  const store = useWorkspaceStore()
  await store.initialize()
  expect(store.ready).toBe(false)
  await store.initialize(profile.user_id)
  expect(fetchMock.mock.calls[1]?.[1]?.method).toBe('PUT')
  expect(store.userId).toBe(profile.user_id)
})

it('allows retry after a backend error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('连接失败')))
  const store = useWorkspaceStore()
  await store.initialize()
  expect(store.ready).toBe(false)
  expect(store.loading).toBe(false)
  expect(store.error).toBe('连接失败')
})
