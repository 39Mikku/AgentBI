/**
 * API type definitions — mirrors AgentBI backend response envelope.
 * Backend returns: { code: number, msg: string, data?: string }
 */

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data?: T
}

export interface SendCodeParams {
  /** 邮箱地址 / 手机号 / 用户名 */
  email: string
}

export interface LoginParams {
  email: string
  code: string
}

/** 业务约定：code === 200 视为成功 */
export const OK = 200
