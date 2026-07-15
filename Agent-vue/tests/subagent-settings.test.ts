import assert from 'node:assert/strict'

const calls: Array<{ url: string; init?: RequestInit }> = []
globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
  calls.push({ url: String(url), init })
  return new Response(
    JSON.stringify({
      capability_id: 'agent.music',
      kind: 'subagent',
      display_name: '音乐子代理',
      description: '音乐',
      config: { search_result_limit: 5, daily_result_limit: 10 },
      fields: [],
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  )
}) as typeof fetch

const api = await import('../src/api/capability-settings.ts')

await api.saveCapabilitySettings('elysia@example.com', 'agent.music', {
  search_result_limit: 5,
  daily_result_limit: 10,
})

assert.equal(
  calls[0]?.url,
  '/api/capabilities/agent.music/settings?user_id=elysia%40example.com',
)
assert.equal(calls[0]?.init?.method, 'PUT')
assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
  config: { search_result_limit: 5, daily_result_limit: 10 },
})
