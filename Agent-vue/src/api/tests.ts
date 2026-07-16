import type { AnswerSelection, AttemptDetail, GenerationState, TestList, TestMode, TestPreferences, TestSession } from './test-types'

const BASE = '/api'
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail || `请求失败 (${response.status})`)
  return body as T
}
const json = (method: string, body: unknown): RequestInit => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const listTests = (userId: string, mode?: TestMode) => request<TestList>(`/tests?user_id=${encodeURIComponent(userId)}${mode ? `&mode=${mode}` : ''}&limit=50`)
export const getTest = (id: string, userId: string) => request<TestSession>(`/tests/${id}?user_id=${encodeURIComponent(userId)}`)
export const createTest = (payload: Record<string, unknown>) => request<TestSession | GenerationState>('/tests', json('POST', payload))
export const getGeneration = (requestId: string, userId: string) => request<GenerationState>(`/tests/creation-requests/${requestId}?user_id=${encodeURIComponent(userId)}`)
export const deleteTest = (id: string, userId: string) => request<void>(`/tests/${id}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' })
export const createAttempt = (testId: string, payload: Record<string, unknown>) => request<AttemptDetail>(`/tests/${testId}/attempts`, json('POST', payload))
export const getAttempt = (id: string, userId: string) => request<AttemptDetail>(`/test-attempts/${id}?user_id=${encodeURIComponent(userId)}`)
export const saveAnswers = (id: string, userId: string, answers: AnswerSelection[]) => request<AttemptDetail>(`/test-attempts/${id}/answers`, json('PATCH', { user_id: userId, answers }))
export const submitAttempt = (id: string, userId: string, answers: AnswerSelection[]) => request<AttemptDetail>(`/test-attempts/${id}/submit`, json('POST', { user_id: userId, request_id: crypto.randomUUID(), answers }))
export const retryAnalysis = (id: string, userId: string) => request<AttemptDetail>(`/test-attempts/${id}/retry-analysis`, json('POST', { user_id: userId, request_id: crypto.randomUUID() }))
export const getPreferences = (userId: string) => request<TestPreferences>(`/tests/preferences?user_id=${encodeURIComponent(userId)}`)
export const savePreferences = (payload: TestPreferences) => request<TestPreferences>('/tests/preferences', json('PUT', {
  user_id: payload.user_id,
  generation_provider_id: payload.generation_provider_id ?? null,
  generation_model: payload.generation_model ?? null,
  analysis_provider_id: payload.analysis_provider_id ?? null,
  analysis_model: payload.analysis_model ?? null,
}))
