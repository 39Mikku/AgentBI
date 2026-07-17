<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandMark from '@/components/brand/BrandMark.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { authenticatedDestination } from '@/home/home-auth-route'
import { getLoginStepPresentation } from '@/login/login-presentation'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const emailRe = /^[\w.+-]+@[\w-]+\.[\w.-]+$/
const emailValid = computed(() => emailRe.test(auth.email.trim()))
const presentation = computed(() => getLoginStepPresentation(auth.step))

function onEnter() {
  if (auth.step === 1 && emailValid.value && auth.canSendCode) {
    void auth.handleSendCode()
  } else if (auth.step === 2 && auth.canLogin) {
    void auth.handleLogin()
  }
}

function goHome() {
  void router.push('/')
}

onMounted(() => {
  if (auth.isAuthenticated) {
    void router.replace(authenticatedDestination(route.query.redirect))
  }
})

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (authenticated) void router.replace(authenticatedDestination(route.query.redirect))
  },
)
</script>

<template>
  <main class="login-page">
    <aside class="brand-stage" aria-label="AgentBI 品牌介绍">
      <div class="stage-grid" aria-hidden="true"></div>
      <div class="stage-scan" aria-hidden="true"></div>

      <header class="stage-header">
        <button class="brand-lockup" type="button" aria-label="返回 AgentBI 首页" @click="goHome">
          <span class="brand-lockup__mark"><BrandMark tone="inverse" /></span>
          <span class="brand-lockup__word">AgentBI</span>
        </button>
        <span class="stage-index">ACCESS NODE / 04</span>
      </header>

      <section class="stage-copy">
        <p class="stage-kicker"><i></i> PERSONAL AI WORKBENCH</p>
        <h1>
          一处入口，<br />
          回到你的<span>智能工作空间。</span>
        </h1>
        <p class="stage-summary">
          对话、角色、实时语音与工具流都已就位。验证身份后，继续上一次没有结束的工作。
        </p>
      </section>

      <div class="stage-diagram" aria-hidden="true">
        <span class="diagram-label label-input">IDENTITY</span>
        <span class="diagram-label label-core">AGENTBI</span>
        <span class="diagram-label label-output">WORKSPACE</span>
        <i class="diagram-line line-a"></i>
        <i class="diagram-line line-b"></i>
        <i class="diagram-node node-a"></i>
        <i class="diagram-node node-b"></i>
        <i class="diagram-node node-c"></i>
        <div class="diagram-core"><BrandMark tone="inverse" label="" /></div>
      </div>

      <footer class="stage-footer">
        <span><i></i> LOCAL SYSTEM READY</span>
        <span>ELYISAREAL.ME / 2026</span>
      </footer>
    </aside>

    <section class="login-workspace">
      <header class="workspace-header">
        <button class="mobile-brand" type="button" aria-label="返回 AgentBI 首页" @click="goHome">
          <span><BrandMark tone="inverse" /></span>
          <b>AgentBI</b>
        </button>

        <button class="back-home" type="button" @click="goHome">
          <span aria-hidden="true">←</span>
          返回首页
        </button>

        <div class="workspace-actions">
          <span class="workspace-status"><i></i> LOGIN CHANNEL</span>
          <ThemeToggle />
        </div>
      </header>

      <div class="login-frame">
        <div class="frame-rule" aria-hidden="true">
          <span :class="{ active: auth.step === 1 }"></span>
          <span :class="{ active: auth.step === 2 }"></span>
        </div>

        <div class="frame-meta">
          <span>{{ presentation.eyebrow }}</span>
          <span>{{ presentation.index }}</span>
        </div>

        <div class="form-heading">
          <p>AUTHENTICATE / CONTINUE</p>
          <h2>{{ presentation.title }}</h2>
          <p class="form-description">
            {{ presentation.description }}
            <template v-if="auth.step === 2">
              <span class="email-reference">{{ auth.email }}</span>
            </template>
          </p>
        </div>

        <Transition name="step" mode="out-in">
          <form v-if="auth.step === 1" key="email" class="login-form" @submit.prevent="onEnter">
            <label class="field" :class="{ invalid: auth.email.length > 0 && !emailValid }">
              <span class="field-meta">
                <span>邮箱地址</span>
                <span>EMAIL / USER ID</span>
              </span>
              <span class="field-control">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <rect x="2.75" y="4.75" width="18.5" height="14.5" rx="1.5" />
                  <path d="m4 7 8 6 8-6" />
                </svg>
                <input
                  v-model="auth.email"
                  type="email"
                  inputmode="email"
                  autocomplete="username"
                  placeholder="you@example.com"
                  aria-label="邮箱地址"
                />
                <span class="field-state">{{ emailValid ? 'VALID' : 'REQUIRED' }}</span>
              </span>
              <span v-if="auth.email.length > 0 && !emailValid" class="field-hint">
                请输入完整的邮箱地址
              </span>
            </label>

            <button
              class="primary-action"
              type="submit"
              :disabled="!auth.canSendCode || !emailValid"
            >
              <span v-if="auth.sending" class="action-loader" aria-hidden="true"></span>
              <span>{{ auth.sending ? '正在建立通道' : presentation.actionLabel }}</span>
              <span v-if="!auth.sending" class="action-arrow" aria-hidden="true">↗</span>
            </button>
          </form>

          <form v-else key="code" class="login-form" @submit.prevent="onEnter">
            <label class="field">
              <span class="field-meta">
                <span>一次性验证码</span>
                <span>ONE-TIME CODE</span>
              </span>
              <span class="field-control code-control">
                <input
                  v-model="auth.code"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="8"
                  placeholder="••••••"
                  aria-label="一次性验证码"
                />
                <span class="field-state">{{ auth.code.trim().length }}/8</span>
              </span>
            </label>

            <button class="primary-action" type="submit" :disabled="!auth.canLogin">
              <span v-if="auth.logging" class="action-loader" aria-hidden="true"></span>
              <span>{{ auth.logging ? '正在核验身份' : presentation.actionLabel }}</span>
              <span v-if="!auth.logging" class="action-arrow" aria-hidden="true">↗</span>
            </button>

            <div class="form-secondary">
              <button type="button" @click="auth.backToEmail">
                <span aria-hidden="true">←</span> 更换邮箱
              </button>
              <button
                type="button"
                :disabled="auth.countdown > 0 || auth.sending"
                @click="auth.handleSendCode"
              >
                {{ auth.countdown > 0 ? `${auth.countdown}s 后可重发` : '重新发送验证码' }}
              </button>
            </div>
          </form>
        </Transition>

        <div class="alert-stack" aria-live="polite">
          <Transition name="alert">
            <div v-if="auth.errorMsg" class="status-alert is-error" role="alert">
              <span>!</span>
              <p>{{ auth.errorMsg }}</p>
            </div>
          </Transition>
          <Transition name="alert">
            <div v-if="auth.successMsg" class="status-alert is-success" role="status">
              <span>✓</span>
              <p>{{ auth.successMsg }}</p>
            </div>
          </Transition>
        </div>

        <div class="login-notes">
          <span>01</span>
          <p>验证码有效期为 5 分钟</p>
          <span>02</span>
          <p>登录状态仅保留在当前浏览器</p>
        </div>
      </div>

      <footer class="workspace-footer">
        <span>AGENTBI / PERSONAL INTELLIGENCE SYSTEM</span>
        <span>SECURE ACCESS · LOCAL FIRST</span>
      </footer>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  --login-ink: #11110f;
  --login-paper: #f1efe8;
  --login-acid: #ccff24;
  --login-muted: #777970;
  --login-line: #c9c8c0;
  display: grid;
  grid-template-columns: minmax(430px, 46vw) minmax(480px, 1fr);
  min-height: 100vh;
  overflow: hidden;
  background: var(--login-paper);
  color: var(--login-ink);
}

button,
input {
  font: inherit;
}

.brand-stage {
  position: relative;
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 32px clamp(32px, 4vw, 68px);
  background: var(--login-ink);
  color: var(--login-paper);
  isolation: isolate;
}

.stage-grid,
.stage-scan {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.stage-grid {
  z-index: -3;
  background-image:
    linear-gradient(rgb(241 239 232 / 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgb(241 239 232 / 0.055) 1px, transparent 1px);
  background-size: 48px 48px;
}

.stage-grid::after {
  position: absolute;
  right: -22%;
  bottom: -34%;
  width: 74%;
  aspect-ratio: 1;
  border: 1px solid rgb(204 255 36 / 0.5);
  border-radius: 50%;
  box-shadow:
    0 0 0 70px rgb(204 255 36 / 0.035),
    0 0 0 140px rgb(204 255 36 / 0.02);
  content: '';
}

.stage-scan {
  z-index: -1;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent 2%, rgb(204 255 36 / 0.8), transparent 88%);
  box-shadow: 0 0 28px rgb(204 255 36 / 0.24);
  animation: stage-scan 7s linear infinite;
}

.stage-header,
.stage-footer,
.workspace-header,
.workspace-footer,
.frame-meta,
.field-meta,
.form-secondary,
.login-notes,
.stage-kicker,
.form-heading > p:first-child {
  font-family: var(--font-mono);
}

.stage-header,
.stage-footer,
.workspace-header,
.workspace-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stage-header,
.stage-copy,
.stage-diagram,
.stage-footer {
  position: relative;
  z-index: 1;
}

.brand-lockup,
.mobile-brand {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.brand-lockup {
  gap: 12px;
}

.brand-lockup__mark {
  width: 35px;
  height: 35px;
}

.brand-lockup__word {
  font: 750 19px var(--font-display);
  letter-spacing: -0.055em;
}

.stage-index {
  color: rgb(241 239 232 / 0.44);
  font: 10px var(--font-mono);
  letter-spacing: 0.16em;
}

.stage-copy {
  max-width: 620px;
  margin-top: clamp(48px, 10vh, 110px);
  animation: rise-in 700ms 80ms cubic-bezier(0.2, 0.75, 0.2, 1) both;
}

.stage-kicker {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 20px;
  color: rgb(241 239 232 / 0.5);
  font-size: 10px;
  letter-spacing: 0.16em;
}

.stage-kicker i {
  width: 25px;
  height: 2px;
  background: var(--login-acid);
}

.stage-copy h1 {
  max-width: 650px;
  margin: 0;
  font: 650 clamp(45px, 5vw, 76px) / 0.96 var(--font-display);
  letter-spacing: -0.075em;
}

.stage-copy h1 span {
  display: inline-block;
  color: var(--login-acid);
}

.stage-summary {
  max-width: 470px;
  margin: 28px 0 0;
  color: rgb(241 239 232 / 0.55);
  font-size: 14px;
  line-height: 1.75;
}

.stage-diagram {
  width: min(100%, 560px);
  height: 152px;
  margin: clamp(35px, 6vh, 70px) 0 32px;
  border-top: 1px solid rgb(241 239 232 / 0.15);
  border-bottom: 1px solid rgb(241 239 232 / 0.15);
  animation: rise-in 700ms 180ms cubic-bezier(0.2, 0.75, 0.2, 1) both;
}

.diagram-label {
  position: absolute;
  color: rgb(241 239 232 / 0.4);
  font: 8px var(--font-mono);
  letter-spacing: 0.12em;
}

.label-input { left: 0; top: 21px; }
.label-core { left: 50%; top: 21px; transform: translateX(-50%); color: var(--login-acid); }
.label-output { right: 0; top: 21px; }

.diagram-line {
  position: absolute;
  top: 81px;
  height: 1px;
  background: rgb(241 239 232 / 0.22);
}

.line-a { left: 16px; right: calc(50% + 37px); }
.line-b { left: calc(50% + 37px); right: 16px; }

.diagram-node {
  position: absolute;
  top: 77px;
  width: 9px;
  height: 9px;
  border: 1px solid rgb(241 239 232 / 0.5);
  border-radius: 50%;
  background: var(--login-ink);
}

.node-a { left: 10px; }
.node-b { left: 50%; transform: translateX(-50%); border-color: var(--login-acid); }
.node-c { right: 10px; }

.diagram-core {
  position: absolute;
  top: 59px;
  left: 50%;
  width: 45px;
  height: 45px;
  padding: 8px;
  border: 1px solid rgb(204 255 36 / 0.7);
  background: var(--login-ink);
  transform: translateX(-50%);
}

.stage-footer {
  padding-top: 18px;
  border-top: 1px solid rgb(241 239 232 / 0.12);
  color: rgb(241 239 232 / 0.36);
  font-size: 8px;
  letter-spacing: 0.12em;
}

.stage-footer span:first-child {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.stage-footer i,
.workspace-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--login-acid);
  box-shadow: 0 0 0 4px rgb(204 255 36 / 0.09);
}

.login-workspace {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  background:
    linear-gradient(90deg, transparent calc(100% - 1px), rgb(17 17 15 / 0.04) 1px) 0 0 / 54px 100%,
    var(--login-paper);
  color: var(--login-ink);
  transition: background-color 180ms ease, color 180ms ease;
}

:global(.dark) .login-workspace {
  --login-paper: #171714;
  --login-ink: #efede6;
  --login-muted: #9d9d94;
  --login-line: #3a3a34;
  background:
    linear-gradient(90deg, transparent calc(100% - 1px), rgb(239 237 230 / 0.035) 1px) 0 0 / 54px 100%,
    var(--login-paper);
}

.workspace-header {
  min-height: 84px;
  padding: 0 clamp(28px, 4vw, 60px);
  border-bottom: 1px solid var(--login-line);
}

.mobile-brand {
  display: none;
  gap: 9px;
}

.mobile-brand span {
  width: 28px;
  height: 28px;
  padding: 3px;
  background: #11110f;
}

.mobile-brand b {
  font: 750 16px var(--font-display);
  letter-spacing: -0.05em;
}

.back-home {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--login-muted);
  font: 10px var(--font-mono);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: color 160ms ease, transform 160ms ease;
}

.back-home:hover {
  color: var(--login-ink);
  transform: translateX(-3px);
}

.workspace-actions {
  display: flex;
  align-items: center;
  gap: 22px;
}

.workspace-status {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--login-muted);
  font: 9px var(--font-mono);
  letter-spacing: 0.12em;
}

.workspace-actions :deep(.theme-toggle) {
  width: 36px;
  height: 36px;
  border-color: var(--login-line);
  border-radius: 50%;
  background: transparent;
  color: var(--login-ink);
  box-shadow: none;
}

.workspace-actions :deep(.theme-toggle:hover) {
  border-color: var(--login-ink);
}

.login-frame {
  width: min(520px, calc(100% - 56px));
  margin: auto;
  padding: 64px 0 58px;
  animation: rise-in 650ms 110ms cubic-bezier(0.2, 0.75, 0.2, 1) both;
}

.frame-rule {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
  margin-bottom: 13px;
}

.frame-rule span {
  height: 3px;
  background: var(--login-line);
  transition: background-color 220ms ease;
}

.frame-rule span.active {
  background: var(--login-acid);
}

.frame-meta {
  display: flex;
  justify-content: space-between;
  color: var(--login-muted);
  font-size: 8px;
  letter-spacing: 0.14em;
}

.form-heading {
  margin: 66px 0 42px;
}

.form-heading > p:first-child {
  margin: 0 0 13px;
  color: var(--login-muted);
  font-size: 9px;
  letter-spacing: 0.12em;
}

.form-heading h2 {
  margin: 0;
  font: 650 clamp(38px, 4.2vw, 59px) / 0.98 var(--font-display);
  letter-spacing: -0.065em;
}

.form-description {
  max-width: 430px;
  margin: 18px 0 0;
  color: var(--login-muted);
  font-size: 13px;
  line-height: 1.72;
}

.email-reference {
  display: block;
  width: fit-content;
  max-width: 100%;
  overflow: hidden;
  margin-top: 8px;
  padding: 3px 7px;
  background: color-mix(in srgb, var(--login-acid) 35%, transparent);
  color: var(--login-ink);
  font: 10px var(--font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.login-form {
  min-height: 192px;
}

.field {
  display: block;
}

.field-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 9px;
  color: var(--login-muted);
  font-size: 8px;
  letter-spacing: 0.1em;
}

.field-meta span:first-child {
  color: var(--login-ink);
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0;
}

.field-control {
  display: flex;
  height: 62px;
  align-items: center;
  gap: 13px;
  padding: 0 17px;
  border: 1px solid var(--login-ink);
  background: transparent;
  box-shadow: 4px 4px 0 color-mix(in srgb, var(--login-ink) 14%, transparent);
  transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
}

.field-control:focus-within {
  border-color: var(--login-ink);
  box-shadow: 4px 4px 0 var(--login-acid);
  transform: translate(-2px, -2px);
}

.field.invalid .field-control {
  border-color: #d43b31;
}

.field-control svg {
  width: 20px;
  flex: 0 0 auto;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.4;
}

.field-control input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--login-ink);
  font: 500 16px var(--font-sans);
}

.field-control input::placeholder {
  color: color-mix(in srgb, var(--login-muted) 68%, transparent);
}

.field-state {
  color: var(--login-muted);
  font: 8px var(--font-mono);
  letter-spacing: 0.08em;
}

.field-hint {
  display: block;
  margin-top: 9px;
  color: #c5352c;
  font-size: 11px;
}

.code-control input {
  text-align: center;
  font: 700 25px var(--font-mono);
  letter-spacing: 0.36em;
  text-indent: 0.36em;
}

.primary-action {
  display: flex;
  width: 100%;
  height: 58px;
  align-items: center;
  justify-content: space-between;
  margin-top: 22px;
  padding: 0 18px 0 22px;
  border: 1px solid var(--login-ink);
  border-radius: 2px;
  background: var(--login-ink);
  color: var(--login-paper);
  font: 700 11px var(--font-mono);
  letter-spacing: 0.06em;
  cursor: pointer;
  box-shadow: 5px 5px 0 var(--login-acid);
  transition: box-shadow 160ms ease, transform 160ms ease, opacity 160ms ease;
}

.primary-action:hover:not(:disabled) {
  box-shadow: 2px 2px 0 var(--login-acid);
  transform: translate(3px, 3px);
}

.primary-action:focus-visible,
.back-home:focus-visible,
.form-secondary button:focus-visible,
.brand-lockup:focus-visible,
.mobile-brand:focus-visible {
  outline: 2px solid var(--login-acid);
  outline-offset: 4px;
}

.primary-action:disabled {
  cursor: not-allowed;
  opacity: 0.34;
  box-shadow: 3px 3px 0 var(--login-line);
}

.action-arrow {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border-radius: 50%;
  background: var(--login-acid);
  color: #11110f;
  font-size: 15px;
}

.action-loader {
  width: 15px;
  height: 15px;
  border: 1px solid rgb(241 239 232 / 0.3);
  border-top-color: var(--login-acid);
  border-radius: 50%;
  animation: spin 700ms linear infinite;
}

.form-secondary {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
}

.form-secondary button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--login-muted);
  font-size: 9px;
  letter-spacing: 0.06em;
  cursor: pointer;
}

.form-secondary button:hover:not(:disabled) {
  color: var(--login-ink);
}

.form-secondary button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.alert-stack {
  display: grid;
  min-height: 46px;
  margin-top: 22px;
}

.status-alert {
  display: grid;
  grid-template-columns: 32px 1fr;
  align-items: stretch;
  border: 1px solid var(--login-line);
  font-size: 11px;
}

.status-alert > span {
  display: grid;
  place-items: center;
  border-right: 1px solid var(--login-line);
  font: 700 12px var(--font-mono);
}

.status-alert p {
  margin: 0;
  padding: 11px 13px;
}

.status-alert.is-error > span {
  background: #ff5a4d;
  color: #11110f;
}

.status-alert.is-success > span {
  background: var(--login-acid);
  color: #11110f;
}

.login-notes {
  display: grid;
  grid-template-columns: 22px 1fr 22px 1fr;
  gap: 9px;
  align-items: baseline;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--login-line);
  color: var(--login-muted);
  font-size: 8px;
  letter-spacing: 0.05em;
}

.login-notes span {
  color: var(--login-ink);
}

.login-notes p {
  margin: 0;
}

.workspace-footer {
  min-height: 62px;
  padding: 0 clamp(28px, 4vw, 60px);
  border-top: 1px solid var(--login-line);
  color: var(--login-muted);
  font: 8px var(--font-mono);
  letter-spacing: 0.1em;
}

.step-enter-active,
.step-leave-active {
  transition: opacity 180ms ease, transform 220ms cubic-bezier(0.2, 0.75, 0.2, 1);
}

.step-enter-from {
  opacity: 0;
  transform: translateX(18px);
}

.step-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.alert-enter-active,
.alert-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.alert-enter-from,
.alert-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

@keyframes rise-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes stage-scan {
  from { transform: translateY(-3px); }
  to { transform: translateY(100vh); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1100px) {
  .login-page {
    grid-template-columns: minmax(370px, 42vw) minmax(450px, 1fr);
  }

  .brand-stage {
    padding-inline: 34px;
  }

  .stage-copy h1 {
    font-size: clamp(40px, 5vw, 58px);
  }

  .stage-diagram {
    height: 130px;
  }

  .diagram-line { top: 70px; }
  .diagram-node { top: 66px; }
  .diagram-core { top: 48px; }
}

@media (max-width: 820px) {
  .login-page {
    display: block;
    min-height: 100dvh;
  }

  .brand-stage {
    display: none;
  }

  .login-workspace {
    min-height: 100dvh;
  }

  .workspace-header {
    min-height: 72px;
    padding-inline: 22px;
  }

  .mobile-brand {
    display: inline-flex;
  }

  .back-home {
    display: none;
  }

  .workspace-status {
    display: none;
  }

  .login-frame {
    width: min(520px, calc(100% - 40px));
    padding-block: 44px;
  }

  .form-heading {
    margin: 48px 0 36px;
  }

  .workspace-footer {
    min-height: 54px;
    padding-inline: 22px;
  }

  .workspace-footer span:last-child {
    display: none;
  }
}

@media (max-width: 460px) {
  .login-frame {
    width: calc(100% - 32px);
    padding-top: 34px;
  }

  .form-heading {
    margin-top: 39px;
  }

  .form-heading h2 {
    font-size: 38px;
  }

  .field-control {
    height: 58px;
    padding-inline: 14px;
  }

  .field-state {
    display: none;
  }

  .login-notes {
    grid-template-columns: 22px 1fr;
  }

  .workspace-footer {
    font-size: 7px;
  }
}

@media (min-width: 821px) and (max-height: 840px) {
  .brand-stage {
    padding-block: 24px;
  }

  .stage-copy {
    margin-top: 34px;
  }

  .stage-copy h1 {
    font-size: clamp(42px, 4.35vw, 62px);
  }

  .stage-summary {
    margin-top: 20px;
  }

  .stage-diagram {
    height: 112px;
    margin: 24px 0 18px;
  }

  .diagram-label {
    top: 14px;
  }

  .diagram-line {
    top: 60px;
  }

  .diagram-node {
    top: 56px;
  }

  .diagram-core {
    top: 38px;
  }

  .workspace-header {
    min-height: 68px;
  }

  .login-frame {
    padding: 34px 0 26px;
  }

  .form-heading {
    margin: 38px 0 28px;
  }

  .form-heading h2 {
    font-size: clamp(40px, 3.7vw, 53px);
  }

  .login-form {
    min-height: 174px;
  }

  .alert-stack {
    min-height: 38px;
    margin-top: 14px;
  }

  .login-notes {
    margin-top: 12px;
    padding-top: 12px;
  }

  .workspace-footer {
    min-height: 48px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
