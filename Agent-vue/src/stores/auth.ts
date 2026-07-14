import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as api from '@/api'
import { ApiError } from '@/api'
import type { UserProfile } from '@/api/user-profile'

const STORAGE_KEY = 'agentbi_auth'
const USER_STORAGE_KEY = 'agentbi_user'
const PROFILE_STORAGE_KEY = 'agentbi_user_profile'

type Step = 1 | 2

export const useAuthStore = defineStore('auth', () => {
  // ---- state ----
  const email = ref(typeof localStorage !== 'undefined' ? localStorage.getItem(USER_STORAGE_KEY) || '' : '')
  const profile = ref<UserProfile | null>(readStoredProfile(email.value))
  const code = ref('')
  const step = ref<Step>(1)
  const sending = ref(false)
  const logging = ref(false)
  const errorMsg = ref('')
  const successMsg = ref('')
  /** 验证码倒计时秒数，0 表示可重新发送 */
  const countdown = ref(0)

  const isAuthenticated = ref<boolean>(
    typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY) === '1',
  )

  let timer: ReturnType<typeof setInterval> | null = null

  function readStoredProfile(userId: string): UserProfile | null {
    if (typeof localStorage === 'undefined') return null
    try {
      const stored = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) || 'null') as UserProfile | null
      return stored?.user_id === userId ? stored : null
    } catch { return null }
  }

  function setProfile(value: UserProfile) {
    profile.value = value
    if (typeof localStorage !== 'undefined') localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(value))
  }

  // ---- getters ----
  const canSendCode = computed(
    () => email.value.trim().length > 0 && !sending.value && countdown.value === 0,
  )
  const canLogin = computed(
    () => code.value.trim().length >= 4 && !logging.value && email.value.trim().length > 0,
  )

  // ---- actions ----
  function notifyError(msg: string) {
    errorMsg.value = msg
    successMsg.value = ''
  }

  function notifySuccess(msg: string) {
    successMsg.value = msg
    errorMsg.value = ''
  }

  function clearNotify() {
    errorMsg.value = ''
    successMsg.value = ''
  }

  function startCountdown(sec = 60) {
    countdown.value = sec
    if (timer) clearInterval(timer)
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        countdown.value = 0
        if (timer) {
          clearInterval(timer)
          timer = null
        }
      }
    }, 1000)
  }

  async function handleSendCode() {
    if (!canSendCode.value) return
    clearNotify()
    sending.value = true
    try {
      const resp = await api.sendCode({ email: email.value.trim() })
      notifySuccess(resp.msg || '验证码已发送，请查收邮件')
      step.value = 2
      startCountdown(60)
    } catch (e) {
      notifyError(e instanceof ApiError ? e.message : '验证码发送失败')
    } finally {
      sending.value = false
    }
  }

  async function handleLogin() {
    if (!canLogin.value) return
    clearNotify()
    logging.value = true
    try {
      const resp = await api.login({ email: email.value.trim(), code: code.value.trim() })
      isAuthenticated.value = true
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, '1')
        localStorage.setItem(USER_STORAGE_KEY, email.value.trim())
        localStorage.removeItem(PROFILE_STORAGE_KEY)
      }
      profile.value = null
      notifySuccess(resp.msg || '登录成功')
    } catch (e) {
      notifyError(e instanceof ApiError ? e.message : '登录失败')
    } finally {
      logging.value = false
    }
  }

  function backToEmail() {
    step.value = 1
    code.value = ''
    clearNotify()
  }

  function logout() {
    isAuthenticated.value = false
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(USER_STORAGE_KEY)
      localStorage.removeItem(PROFILE_STORAGE_KEY)
    }
    resetForm()
  }

  function resetForm() {
    email.value = ''
    profile.value = null
    code.value = ''
    step.value = 1
    countdown.value = 0
    clearNotify()
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return {
    email,
    profile,
    code,
    step,
    sending,
    logging,
    errorMsg,
    successMsg,
    countdown,
    isAuthenticated,
    canSendCode,
    canLogin,
    handleSendCode,
    handleLogin,
    setProfile,
    backToEmail,
    logout,
    resetForm,
    clearNotify,
  }
})
