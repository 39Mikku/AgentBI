/**
 * AgentBI API service layer.
 *
 * All requests are proxied through Vite dev server (/api -> http://127.0.0.1:8000)
 * to avoid CORS during development. In production, configure the reverse proxy
 * to strip the /api prefix before forwarding to the FastAPI backend.
 */
import type { ApiResponse, LoginParams, SendCodeParams } from './types'
import { OK } from './types'

const BASE = '/api'

class ApiError extends Error {
  code: number
  constructor(code: number, msg: string) {
    super(msg)
    this.name = 'ApiError'
    this.code = code
  }
}

async function request<T>(path: string, body: Record<string, unknown>): Promise<ApiResponse<T>> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, '网络连接失败，请确认后端服务已启动 (127.0.0.1:8000)')
  }

  if (!res.ok) {
    throw new ApiError(res.status, `服务异常 (HTTP ${res.status})`)
  }

  const payload = (await res.json()) as ApiResponse<T>
  return payload
}

/** 发送验证码到用户邮箱 */
export async function sendCode(params: SendCodeParams): Promise<ApiResponse> {
  const resp = await request('/send_code', { email: params.email })
  if (resp.code !== OK) {
    throw new ApiError(resp.code, resp.msg || '验证码发送失败')
  }
  return resp
}

/** 校验邮箱 + 验证码，完成登录 */
export async function login(params: LoginParams): Promise<ApiResponse> {
  const resp = await request('/login', { email: params.email, code: params.code })
  if (resp.code !== OK) {
    throw new ApiError(resp.code, resp.msg || '登录失败')
  }
  return resp
}

export { ApiError }
