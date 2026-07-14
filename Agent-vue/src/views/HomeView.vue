<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const auth = useAuthStore()

const emailRe = /^[\w.+-]+@[\w-]+\.[\w.-]+$/
const emailValid = computed(() => emailRe.test(auth.email.trim()))

const features = [
  { k: '01', t: '邮件智能投递', d: '大模型自主决策收件人与正文' },
  { k: '02', t: '数据库实时查询', d: '自然语言到字段级查询的映射' },
  { k: '03', t: '验证码秒级触达', d: 'Redis 双向绑定，TTL 300s' },
  { k: '04', t: '上下文持久记忆', d: 'MemorySaver 跨轮次 checkpoint' },
]

function onEnter() {
  if (auth.step === 1 && emailValid.value && auth.canSendCode) {
    auth.handleSendCode()
  } else if (auth.step === 2 && auth.canLogin) {
    auth.handleLogin()
  }
}

onMounted(() => {
  if (auth.isAuthenticated) {
    router.replace('/chat')
  }
})

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (authenticated) router.replace('/chat')
  },
)
</script>

<template>
  <div class="auth-shell">
    <!-- ===== left: brand visual ===== -->
    <aside class="auth-visual">
      <div class="visual-grid" aria-hidden="true"></div>
      <div class="visual-glow glow-a" aria-hidden="true"></div>
      <div class="visual-glow glow-b" aria-hidden="true"></div>
      <div class="visual-scanlines" aria-hidden="true"></div>

      <div class="visual-content">
        <div class="brand-mark">
          <span class="brand-glyph">
            <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path
                d="M16 3l11 6v14l-11 6L5 23V9l11-6z"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linejoin="round"
              />
              <path
                d="M16 3v26M5 9l11 6 11-6M5 23l11-6 11 6"
                stroke="currentColor"
                stroke-width="1.1"
                stroke-linejoin="round"
                opacity="0.55"
              />
              <circle cx="16" cy="15" r="2.4" fill="currentColor" />
            </svg>
          </span>
          <span class="brand-name">AgentBI</span>
        </div>

        <div class="visual-headline">
          <p class="headline-eyebrow">智能体中枢 · Agent Console</p>
          <h2 class="headline-title">
            以大模型为大脑<br />
            <span class="title-accent">重构</span>业务自动化
          </h2>
          <p class="headline-sub">
            将离散的工具脚本沉淀为企业级 FastAPI 智能体微服务——
            从用户查询、验证码生成到邮件投递，全链路由模型自主决策。
          </p>
        </div>

        <ul class="feature-list">
          <li v-for="f in features" :key="f.k" class="feature-item">
            <span class="feature-key">{{ f.k }}</span>
            <div class="feature-text">
              <span class="feature-t">{{ f.t }}</span>
              <span class="feature-d">{{ f.d }}</span>
            </div>
          </li>
        </ul>
      </div>

      <div class="visual-footer">
        <span class="footer-pulse"></span>
        <span class="footer-text">系统在线 · 后端服务 127.0.0.1:8000</span>
      </div>
    </aside>

    <!-- ===== right: form panel ===== -->
    <section class="auth-panel">
      <div class="panel-top">
        <div class="panel-brand-group">
          <span class="panel-brand">AgentBI</span>
          <button class="home-link" type="button" @click="router.push('/')">
            <span aria-hidden="true">←</span> 返回首页
          </button>
        </div>
        <ThemeToggle />
      </div>

      <div class="panel-form">
        <div class="form-head">
          <span class="form-step">
            <i class="step-bar"></i>
            步骤 {{ String(auth.step).padStart(2, '0') }} / 02
          </span>
          <h1 class="form-title">{{ auth.step === 1 ? '验证身份以继续' : '输入验证码' }}</h1>
          <p class="form-desc">
            <template v-if="auth.step === 1">
              输入你的邮箱地址，系统将经由智能体核验后发送一次性验证码。
            </template>
            <template v-else>
              验证码已发送至 <span class="email-chip">{{ auth.email }}</span
              >，请查收邮件并填入下方。
            </template>
          </p>
        </div>

        <!-- step 1: email -->
        <div v-if="auth.step === 1" class="step-body" style="animation: fade-up 0.45s ease both">
          <label class="field" :class="{ invalid: auth.email.length > 0 && !emailValid }">
            <span class="field-label">邮箱地址 / 用户名</span>
            <div class="field-control">
              <svg
                class="field-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <rect x="3" y="5" width="18" height="14" rx="2.5" />
                <path d="M4 7l8 6 8-6" />
              </svg>
              <input
                v-model="auth.email"
                type="text"
                inputmode="email"
                autocomplete="username"
                placeholder="you@example.com"
                class="field-input"
                @keyup.enter="onEnter"
              />
            </div>
            <span v-if="auth.email.length > 0 && !emailValid" class="field-hint">
              邮箱格式似乎不太对
            </span>
          </label>

          <button
            class="btn-primary"
            type="button"
            :disabled="!auth.canSendCode || (!emailValid && auth.email.length > 0)"
            @click="auth.handleSendCode"
          >
            <span v-if="auth.sending" class="spinner" aria-hidden="true"></span>
            <span>{{ auth.sending ? '发送中…' : '发送验证码' }}</span>
            <svg
              v-if="!auth.sending"
              class="btn-arrow"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>

        <!-- step 2: code -->
        <div v-else class="step-body" style="animation: fade-up 0.45s ease both">
          <label class="field">
            <span class="field-label">验证码</span>
            <div class="field-control code-control">
              <input
                v-model="auth.code"
                type="text"
                inputmode="numeric"
                autocomplete="one-time-code"
                maxlength="8"
                placeholder="••••••"
                class="field-input code-input"
                @keyup.enter="onEnter"
              />
            </div>
          </label>

          <button
            class="btn-primary"
            type="button"
            :disabled="!auth.canLogin"
            @click="auth.handleLogin"
          >
            <span v-if="auth.logging" class="spinner" aria-hidden="true"></span>
            <span>{{ auth.logging ? '核验中…' : '登录控制台' }}</span>
            <svg
              v-if="!auth.logging"
              class="btn-arrow"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>

          <div class="step-foot">
            <button class="link-btn" type="button" @click="auth.backToEmail">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M19 12H5M11 18l-6-6 6-6" />
              </svg>
              更换邮箱
            </button>
            <button
              class="link-btn"
              type="button"
              :disabled="auth.countdown > 0"
              @click="auth.handleSendCode"
            >
              {{ auth.countdown > 0 ? `${auth.countdown}s 后可重发` : '重新发送' }}
            </button>
          </div>
        </div>

        <!-- alerts -->
        <Transition name="alert">
          <div v-if="auth.errorMsg" class="alert alert-error" role="alert">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <span>{{ auth.errorMsg }}</span>
          </div>
        </Transition>
        <Transition name="alert">
          <div v-if="auth.successMsg" class="alert alert-success" role="status">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M8.5 12.5l2.5 2.5 4.5-5" />
            </svg>
            <span>{{ auth.successMsg }}</span>
          </div>
        </Transition>
      </div>

      <div class="panel-footer">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M12 3l7 3v5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6l7-3z" />
        </svg>
        <span>验证码经加密通道传输，登录态仅存于本地浏览器</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth-shell {
  display: flex;
  min-height: 100vh;
  background: var(--background);
}

/* ============ LEFT VISUAL ============ */
.auth-visual {
  position: relative;
  flex: 0 0 var(--auth-visual-w);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(2rem, 4vw, 3.2rem);
  overflow: hidden;
  background: #06070a;
  color: #f5f5f7;
}

.visual-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  -webkit-mask-image: radial-gradient(ellipse 80% 70% at 50% 38%, #000 35%, transparent 78%);
  mask-image: radial-gradient(ellipse 80% 70% at 50% 38%, #000 35%, transparent 78%);
  animation: drift 14s ease-in-out infinite;
}

.visual-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  pointer-events: none;
}
.glow-a {
  width: 520px;
  height: 520px;
  top: -120px;
  left: -80px;
  background: radial-gradient(circle, rgba(0, 122, 255, 0.5), transparent 65%);
  animation: pulse-ring 7s ease-in-out infinite;
}
.glow-b {
  width: 420px;
  height: 420px;
  bottom: -100px;
  right: -60px;
  background: radial-gradient(circle, rgba(46, 141, 255, 0.32), transparent 65%);
  animation: pulse-ring 9s ease-in-out infinite 1.5s;
}

.visual-scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent 0,
    transparent 3px,
    rgba(255, 255, 255, 0.012) 3px,
    rgba(255, 255, 255, 0.012) 4px
  );
  pointer-events: none;
}

.visual-content {
  position: relative;
  z-index: 2;
  animation: fade-up 0.8s ease both;
}

.brand-mark {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: clamp(2.5rem, 6vh, 4.5rem);
}
.brand-glyph {
  display: inline-flex;
  width: 34px;
  height: 34px;
  color: var(--brand-400);
  filter: drop-shadow(0 0 12px rgba(0, 122, 255, 0.55));
}
.brand-glyph svg {
  width: 100%;
  height: 100%;
}
.brand-name {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.15rem;
  letter-spacing: -0.01em;
}

.visual-headline {
  max-width: 30ch;
}
.headline-eyebrow {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--brand-300);
  margin-bottom: 1.1rem;
}
.headline-title {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: clamp(1.9rem, 3.4vw, 2.7rem);
  line-height: 1.1;
  letter-spacing: -0.025em;
}
.title-accent {
  background: linear-gradient(100deg, var(--brand-300), #66abff 60%, #2e8dff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.headline-sub {
  margin-top: 1.1rem;
  color: rgba(245, 245, 247, 0.58);
  font-size: 0.94rem;
  line-height: 1.65;
}

.feature-list {
  list-style: none;
  margin-top: clamp(2rem, 5vh, 3.2rem);
  display: grid;
  gap: 0.85rem;
}
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.9rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.025);
  backdrop-filter: blur(6px);
  transition:
    border-color 0.3s ease,
    background-color 0.3s ease;
}
.feature-item:hover {
  border-color: rgba(0, 122, 255, 0.4);
  background: rgba(0, 122, 255, 0.06);
}
.feature-key {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  font-weight: 500;
  color: var(--brand-300);
  letter-spacing: 0.08em;
  padding-top: 0.15rem;
}
.feature-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.feature-t {
  font-weight: 600;
  font-size: 0.92rem;
  color: #f5f5f7;
}
.feature-d {
  font-size: 0.78rem;
  color: rgba(245, 245, 247, 0.45);
}

.visual-footer {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  color: rgba(245, 245, 247, 0.4);
  letter-spacing: 0.03em;
}
.footer-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--state-success);
  box-shadow: 0 0 0 3px rgba(52, 199, 89, 0.18);
  animation: pulse-ring 2.5s ease-in-out infinite;
}

/* ============ RIGHT PANEL ============ */
.auth-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem clamp(1.5rem, 4vw, 3rem);
}
.panel-brand-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.panel-brand {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
  color: var(--foreground);
}
.home-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--muted-foreground);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    color 0.2s ease,
    transform 0.2s ease;
}
.home-link:hover {
  color: var(--primary);
  transform: translateX(-2px);
}

.panel-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  padding: 1rem clamp(1.5rem, 4vw, 3rem) 2rem;
}

.form-head {
  margin-bottom: 2rem;
  animation: fade-up 0.6s ease both;
}
.form-step {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted-foreground);
  margin-bottom: 1rem;
}
.step-bar {
  display: inline-block;
  width: 28px;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(
    90deg,
    var(--primary),
    color-mix(in srgb, var(--primary) 20%, transparent)
  );
}
.form-title {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  line-height: 1.1;
  letter-spacing: -0.025em;
  color: var(--foreground);
}
.form-desc {
  margin-top: 0.7rem;
  color: var(--muted-foreground);
  font-size: 0.95rem;
  line-height: 1.6;
}
.email-chip {
  font-family: var(--font-mono);
  font-size: 0.86em;
  color: var(--foreground);
  background: var(--muted);
  padding: 0.1em 0.5em;
  border-radius: 0.4rem;
}

/* ---- field ---- */
.field {
  display: block;
  margin-bottom: 1.3rem;
}
.field-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--foreground);
  margin-bottom: 0.55rem;
  letter-spacing: 0.01em;
}
.field-control {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  height: 54px;
  padding: 0 1.1rem;
  border: 1.5px solid var(--input);
  border-radius: var(--radius);
  background: var(--card);
  box-shadow: var(--shadow-xs);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}
.field-control:focus-within {
  border-color: var(--ring);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--ring) 16%, transparent);
}
.field.invalid .field-control {
  border-color: var(--destructive);
}
.field-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  color: var(--muted-foreground);
}
.field-input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--foreground);
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 500;
}
.field-input::placeholder {
  color: var(--muted-foreground);
  font-weight: 400;
}
.field-hint {
  display: block;
  margin-top: 0.45rem;
  font-size: 0.78rem;
  color: var(--destructive);
}

/* code field */
.code-control {
  justify-content: center;
  height: 64px;
}
.code-input {
  text-align: center;
  font-family: var(--font-mono);
  font-size: 1.7rem;
  font-weight: 700;
  letter-spacing: 0.6em;
  text-indent: 0.6em;
}

/* ---- button ---- */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  width: 100%;
  height: 54px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--primary);
  color: var(--primary-foreground);
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: 0.01em;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition:
    filter 0.18s ease,
    transform 0.18s ease,
    opacity 0.18s ease;
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(1.06);
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}
.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-arrow {
  width: 19px;
  height: 19px;
  transition: transform 0.2s ease;
}
.btn-primary:hover:not(:disabled) .btn-arrow {
  transform: translateX(3px);
}

/* ---- step foot ---- */
.step-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.3rem;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: 0;
  background: transparent;
  color: var(--muted-foreground);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.3rem 0;
  transition: color 0.2s ease;
}
.link-btn svg {
  width: 16px;
  height: 16px;
}
.link-btn:hover:not(:disabled) {
  color: var(--primary);
}
.link-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---- alert ---- */
.alert {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 1.2rem;
  padding: 0.8rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.86rem;
  font-weight: 500;
}
.alert svg {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
}
.alert-error {
  background: color-mix(in srgb, var(--destructive) 10%, transparent);
  color: var(--destructive);
  border: 1px solid color-mix(in srgb, var(--destructive) 28%, transparent);
}
.alert-success {
  background: color-mix(in srgb, var(--success) 12%, transparent);
  color: var(--success);
  border: 1px solid color-mix(in srgb, var(--success) 30%, transparent);
}

.alert-enter-active,
.alert-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}
.alert-enter-from,
.alert-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ---- panel footer ---- */
.panel-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem;
  color: var(--muted-foreground);
  font-size: 0.78rem;
}
.panel-footer svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

/* ============ RESPONSIVE ============ */
@media (max-width: 920px) {
  .auth-visual {
    display: none;
  }
  .auth-shell {
    background: var(--background);
  }
  .panel-form {
    max-width: 440px;
  }
}

@media (max-width: 480px) {
  .panel-top,
  .panel-form {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }
  .code-input {
    font-size: 1.4rem;
    letter-spacing: 0.45em;
    text-indent: 0.45em;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
