<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import BrandMark from '@/components/brand/BrandMark.vue'
import ProjectFooter from '@/components/brand/ProjectFooter.vue'
import { getNotFoundPrimaryAction } from '@/project/project-surfaces'

const route = useRoute()
const primaryAction = getNotFoundPrimaryAction()
const attemptedPath = computed(() => route.fullPath)
</script>

<template>
  <main class="not-found-page">
    <header>
      <RouterLink class="not-found-brand" to="/" aria-label="返回 AgentBI 首页">
        <BrandMark tone="inverse" />
        <strong>AgentBI</strong>
      </RouterLink>
      <span>ROUTE RESOLUTION / FAILED</span>
    </header>

    <section class="error-stage">
      <div class="error-meta"><i></i><span>HTTP 404 · NODE NOT FOUND</span></div>
      <p class="error-code" aria-hidden="true">404</p>
      <div class="error-message">
        <span>YOU ARRIVED SOMEWHERE<br />THAT DOESN'T EXIST.</span>
        <h1>这条路径还没有<br /><em>长成页面。</em></h1>
      </div>
      <div class="error-path">
        <small>REQUESTED PATH</small>
        <code>{{ attemptedPath }}</code>
      </div>
      <nav aria-label="404 页面操作">
        <RouterLink class="primary-action" :to="primaryAction.to">{{ primaryAction.label }} <b>↗</b></RouterLink>
        <RouterLink class="secondary-action" to="/">返回首页</RouterLink>
      </nav>
    </section>

    <ProjectFooter class="not-found-footer" tone="dark" compact />
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@600;700;800&family=Playfair+Display:ital,wght@1,600&display=swap');

.not-found-page {
  --error-paper: #f1efe8;
  --error-ink: #11110f;
  --error-acid: #ccff24;
  min-height: 100vh;
  padding: 0 clamp(22px, 4.5vw, 72px);
  overflow: hidden;
  background:
    radial-gradient(circle at 75% 45%, rgb(204 255 36 / .1), transparent 26%),
    linear-gradient(90deg, rgb(241 239 232 / .055) 1px, transparent 1px),
    linear-gradient(rgb(241 239 232 / .045) 1px, transparent 1px),
    var(--error-ink);
  background-size: auto, 48px 48px, 48px 48px, auto;
  color: var(--error-paper);
  font-family: 'Manrope', var(--font-sans), sans-serif;
}

header {
  display: flex;
  min-height: 76px;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgb(241 239 232 / .16);
}

.not-found-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
}

.not-found-brand :deep(.brand-mark) { width: 30px; height: 30px; }
.not-found-brand strong { font-size: 17px; letter-spacing: -.06em; }
header > span { color: rgb(241 239 232 / .36); font: 8px 'DM Mono', monospace; letter-spacing: .12em; }

.error-stage {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(300px, .75fr);
  min-height: calc(100vh - 150px);
  align-content: center;
  gap: 40px 70px;
  padding: 56px 0 96px;
}

.error-meta {
  position: absolute;
  top: 38px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgb(241 239 232 / .45);
  font: 8px 'DM Mono', monospace;
  letter-spacing: .12em;
}

.error-meta i { width: 44px; height: 1px; background: var(--error-acid); }
.error-code { margin: 0; color: var(--error-acid); font-size: clamp(190px, 31vw, 510px); font-weight: 800; letter-spacing: -.14em; line-height: .64; }
.error-message { align-self: end; border-left: 3px solid var(--error-paper); padding-left: 25px; }
.error-message > span { color: rgb(241 239 232 / .42); font: 8px/1.7 'DM Mono', monospace; letter-spacing: .12em; }
.error-message h1 { margin: 28px 0 0; font-size: clamp(33px, 4.3vw, 68px); letter-spacing: -.07em; line-height: 1.02; }
.error-message em { color: var(--error-acid); font-family: 'Playfair Display', serif; font-weight: 600; }
.error-path { align-self: end; display: grid; gap: 12px; }
.error-path small { color: rgb(241 239 232 / .38); font: 8px 'DM Mono', monospace; letter-spacing: .12em; }
.error-path code { max-width: 100%; overflow: hidden; color: var(--error-paper); font: 12px 'DM Mono', monospace; text-overflow: ellipsis; white-space: nowrap; }
.error-stage nav { display: flex; align-items: center; justify-content: flex-end; gap: 18px; }
.error-stage nav a { min-height: 54px; display: inline-flex; align-items: center; justify-content: center; padding: 0 22px; font: var(--control-font-size) 'DM Mono', monospace; letter-spacing: .08em; text-decoration: none; text-transform: uppercase; }
.primary-action { min-width: 190px; justify-content: space-between !important; background: var(--error-acid); color: var(--error-ink); box-shadow: 5px 5px 0 rgb(204 255 36 / .18); }
.primary-action b { font-size: 16px; font-weight: 400; }
.secondary-action { border: 1px solid rgb(241 239 232 / .28); color: var(--error-paper); }
.error-stage nav a:hover { transform: translateY(-2px); }
.error-stage nav a:focus-visible,.not-found-brand:focus-visible { outline: 2px solid var(--error-acid); outline-offset: 5px; }
.not-found-footer { min-height: 74px; }

@media (max-width: 820px) {
  .error-stage { grid-template-columns: 1fr; padding-top: 95px; }
  .error-code { font-size: clamp(170px, 55vw, 350px); }
  .error-message { align-self: start; }
  .error-stage nav { justify-content: flex-start; }
}

@media (max-width: 520px) {
  header > span { display: none; }
  .error-stage { gap: 42px; padding-bottom: 55px; }
  .error-code { font-size: 49vw; }
  .error-stage nav { align-items: stretch; flex-direction: column; }
  .error-stage nav a { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .error-stage nav a { transition: none; }
}
</style>
