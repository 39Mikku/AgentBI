<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import BrandMark from '@/components/brand/BrandMark.vue'
import ProjectFooter from '@/components/brand/ProjectFooter.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { AUTHOR_PARAGRAPHS, PROJECT_AUTHOR, PROJECT_MODULES } from '@/project/project-surfaces'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const workspaceTarget = computed(() => auth.isAuthenticated ? '/home' : '/login')
const workspaceLabel = computed(() => auth.isAuthenticated ? '返回工作空间' : '进入工作台')
</script>

<template>
  <main class="about-page">
    <header class="about-header">
      <RouterLink class="about-brand" to="/" aria-label="返回 AgentBI 首页">
        <BrandMark />
        <strong>AgentBI</strong>
      </RouterLink>
      <nav aria-label="关于页导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink :to="workspaceTarget">{{ workspaceLabel }}</RouterLink>
        <ThemeToggle />
      </nav>
    </header>

    <section class="about-hero">
      <div class="hero-index">
        <span>ABOUT / 01</span>
        <i></i>
        <span>PERSONAL AI WORKBENCH</span>
      </div>
      <h1>
        为自己做，<br />
        <em>因好奇心</em><br />
        继续生长。
      </h1>
      <div class="hero-note">
        <p>AgentBI 不是一个试图装下所有人的产品。</p>
        <p>它是一处把模型、角色、声音、工具和偶然冒出的想法收拢起来的私人工作空间。</p>
        <span>LOCAL FIRST · MULTI MODEL · AGENT READY</span>
      </div>
    </section>

    <section class="origin-section">
      <div class="section-label"><span>02</span><p>ORIGIN / 起点</p></div>
      <blockquote>“这功能要是能<br />直接用就好了。”</blockquote>
      <div class="origin-copy">
        <p>于是一个功能接着一个功能，被放进同一个界面。</p>
        <p>不是为了追逐完整，而是为了让真实使用中的每一次不顺手，都能变成下一次修改的理由。</p>
      </div>
    </section>

    <section class="spaces-section">
      <header class="section-heading">
        <div class="section-label"><span>03</span><p>THE SPACES / 四个空间</p></div>
        <p>同一套身份、配置与本地数据底座，各自承担不同的交互方式。</p>
      </header>
      <div class="space-grid">
        <article v-for="module in PROJECT_MODULES" :key="module.name" :style="{ '--module-accent': module.accent }">
          <div><span>{{ module.index }}</span><i></i><small>{{ module.name.toUpperCase() }}</small></div>
          <h2>{{ module.name }}</h2>
          <p>{{ module.description }}</p>
          <small>{{ module.detail }}</small>
          <RouterLink :to="auth.isAuthenticated ? module.to : '/login'">打开空间 <b>↗</b></RouterLink>
        </article>
      </div>
    </section>

    <section class="architecture-section">
      <div class="section-label"><span>04</span><p>ARCHITECTURE / 当前结构</p></div>
      <div class="architecture-flow" aria-label="AgentBI 技术架构">
        <div class="flow-node primary"><small>INTERFACE</small><strong>Vue 3</strong><span>TypeScript / Vite</span></div>
        <i>→</i>
        <div class="flow-node"><small>APPLICATION</small><strong>FastAPI</strong><span>Agents / Tools / Streaming</span></div>
        <i>→</i>
        <div class="flow-stack">
          <div class="flow-node"><small>LOCAL DATA</small><strong>SQLite</strong><span>Conversation / Memory / Assets</span></div>
          <div class="flow-node accent"><small>MODEL LAYER</small><strong>Providers</strong><span>OpenAI-compatible / Realtime</span></div>
        </div>
      </div>
      <p class="architecture-note">功能可以继续变多，但它们应当共享清晰的数据边界和同一个工作空间，而不是重新长成一组互不相识的页面。</p>
    </section>

    <section class="author-section">
      <div class="author-aside">
        <span>05 / ABOUT THE AUTHOR</span>
        <BrandMark tone="inverse" label="" />
        <small>BUILT FOR MYSELF<br />EXPANDED BY CURIOSITY</small>
      </div>
      <article>
        <p class="author-kicker">关于作者</p>
        <h2>{{ PROJECT_AUTHOR }}<i>。</i></h2>
        <div class="author-copy">
          <p v-for="(paragraph, index) in AUTHOR_PARAGRAPHS.slice(0, -1)" :key="index">{{ paragraph }}</p>
        </div>
        <p class="author-signoff">{{ AUTHOR_PARAGRAPHS.at(-1) }}</p>
      </article>
    </section>

    <ProjectFooter class="about-footer" />
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');

.about-page {
  --about-ink: #11110f;
  --about-paper: #f1efe8;
  --about-muted: #77736b;
  --about-line: #bbb6aa;
  --about-acid: #ccff24;
  min-height: 100vh;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgb(17 17 15 / 0.045) 1px, transparent 1px),
    linear-gradient(rgb(17 17 15 / 0.035) 1px, transparent 1px),
    var(--about-paper);
  background-size: 48px 48px;
  color: var(--about-ink);
  font-family: 'Manrope', var(--font-sans), sans-serif;
}

:global(.dark) .about-page {
  --about-ink: #efede6;
  --about-paper: #151513;
  --about-muted: #9f9b92;
  --about-line: #49473f;
  background:
    linear-gradient(90deg, rgb(241 239 232 / 0.045) 1px, transparent 1px),
    linear-gradient(rgb(241 239 232 / 0.035) 1px, transparent 1px),
    var(--about-paper);
}

.about-header,
.about-hero,
.origin-section,
.spaces-section,
.architecture-section,
.about-footer {
  width: min(1240px, calc(100% - 64px));
  margin-inline: auto;
}

.about-header {
  display: flex;
  min-height: 76px;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--about-line);
}

.about-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
}

.about-brand :deep(.brand-mark) { width: 30px; height: 30px; }
.about-brand strong { font-size: 17px; letter-spacing: -.06em; }
.about-header nav { display: flex; align-items: center; gap: 23px; }
.about-header nav > a { color: var(--about-ink); font: 9px 'DM Mono', monospace; letter-spacing: .08em; text-decoration: none; text-transform: uppercase; }

.about-header a:focus-visible,
.space-grid a:focus-visible {
  outline: 2px solid var(--about-acid);
  outline-offset: 5px;
}

.about-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(270px, .55fr);
  min-height: min(790px, calc(100vh - 76px));
  padding: clamp(70px, 10vh, 120px) 0 80px;
  align-content: space-between;
  column-gap: 60px;
}

.hero-index,
.section-label {
  display: flex;
  align-items: center;
  gap: 13px;
  color: var(--about-muted);
  font: 8px 'DM Mono', monospace;
  letter-spacing: .12em;
}

.hero-index { grid-column: 1 / -1; align-self: start; }
.hero-index i { width: 52px; height: 1px; background: var(--about-acid); }

.about-hero h1 {
  align-self: end;
  margin: 0;
  font-size: clamp(67px, 9.4vw, 145px);
  font-weight: 800;
  letter-spacing: -.085em;
  line-height: .82;
}

.about-hero h1 em { color: var(--about-acid); font-family: 'Playfair Display', serif; font-weight: 600; }
.hero-note { align-self: end; padding: 24px 0 7px 24px; border-left: 3px solid var(--about-ink); }
.hero-note p { margin: 0 0 13px; font-size: 13px; line-height: 1.7; }
.hero-note span { display: block; margin-top: 30px; color: var(--about-muted); font: 8px 'DM Mono', monospace; letter-spacing: .1em; }

.origin-section {
  display: grid;
  grid-template-columns: 190px minmax(0, 1.2fr) minmax(260px, .6fr);
  gap: 45px;
  padding: clamp(80px, 10vw, 150px) 0;
  border-top: 1px solid var(--about-line);
}

.section-label { align-self: start; }
.section-label span { color: var(--about-ink); }
.section-label p { margin: 0; }
.origin-section blockquote { margin: 0; font: 600 clamp(38px, 5.2vw, 78px)/1.08 'Playfair Display', serif; letter-spacing: -.055em; }
.origin-copy { align-self: end; border-top: 1px solid var(--about-line); padding-top: 20px; }
.origin-copy p { margin: 0 0 16px; color: var(--about-muted); font-size: 13px; line-height: 1.8; }

.spaces-section { padding: 110px 0 130px; border-top: 1px solid var(--about-line); }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 30px; margin-bottom: 34px; }
.section-heading > p { width: 360px; margin: 0; color: var(--about-muted); font-size: 12px; line-height: 1.7; }
.space-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--about-ink); border: 1px solid var(--about-ink); }
.space-grid article { --module-accent: var(--about-acid); display: flex; min-height: 430px; flex-direction: column; padding: 24px; background: var(--about-paper); }
.space-grid article > div { display: flex; align-items: center; gap: 10px; font: 8px 'DM Mono', monospace; }
.space-grid article > div i { height: 1px; flex: 1; background: var(--module-accent); }
.space-grid h2 { margin: 78px 0 14px; font-size: clamp(32px, 3.2vw, 52px); letter-spacing: -.065em; }
.space-grid article > p { min-height: 48px; margin: 0; font-size: 13px; font-weight: 700; line-height: 1.55; }
.space-grid article > small { margin-top: 18px; color: var(--about-muted); font-size: 10px; line-height: 1.7; }
.space-grid a { display: flex; align-items: center; justify-content: space-between; margin-top: auto; padding-top: 18px; border-top: 1px solid var(--about-line); color: var(--about-ink); font: 9px 'DM Mono', monospace; text-decoration: none; }
.space-grid a b { display: grid; width: 26px; height: 26px; place-items: center; border-radius: 50%; background: var(--module-accent); color: #11110f; font-weight: 400; transition: transform .2s ease; }
.space-grid a:hover b { transform: rotate(45deg); }

.architecture-section { padding: 110px 0 130px; border-top: 1px solid var(--about-line); }
.architecture-flow { display: grid; grid-template-columns: 1fr auto 1fr auto 1.2fr; align-items: stretch; gap: 18px; margin-top: 48px; }
.architecture-flow > i { align-self: center; color: var(--about-muted); font: 18px 'DM Mono', monospace; }
.flow-stack { display: grid; gap: 1px; background: var(--about-ink); border: 1px solid var(--about-ink); }
.flow-node { display: grid; min-height: 155px; align-content: space-between; padding: 20px; border: 1px solid var(--about-ink); background: var(--about-paper); }
.flow-stack .flow-node { border: 0; }
.flow-node.primary { background: var(--about-ink); color: var(--about-paper); }
.flow-node.accent { background: var(--about-acid); color: #11110f; }
.flow-node small,.flow-node span { font: 8px 'DM Mono', monospace; letter-spacing: .08em; }
.flow-node strong { font-size: clamp(27px, 3vw, 44px); letter-spacing: -.06em; }
.architecture-note { width: min(590px, 100%); margin: 36px 0 0 auto; color: var(--about-muted); font-size: 13px; line-height: 1.8; }

.author-section { display: grid; grid-template-columns: minmax(250px, .55fr) minmax(0, 1.45fr); background: #11110f; color: #f1efe8; }
.author-aside { display: flex; min-height: 720px; flex-direction: column; justify-content: space-between; padding: clamp(38px, 5vw, 70px); border-right: 1px solid rgb(241 239 232 / .16); font: 8px 'DM Mono', monospace; letter-spacing: .1em; }
.author-aside :deep(.brand-mark) { width: clamp(95px, 12vw, 165px); height: auto; }
.author-aside small { color: rgb(241 239 232 / .42); line-height: 1.8; }
.author-section article { padding: clamp(60px, 8vw, 120px); }
.author-kicker { margin: 0 0 26px; color: var(--about-acid); font: 9px 'DM Mono', monospace; letter-spacing: .12em; }
.author-section h2 { margin: 0 0 55px; font-size: clamp(70px, 10vw, 150px); letter-spacing: -.1em; line-height: .8; }
.author-section h2 i { color: var(--about-acid); font-style: normal; }
.author-copy { display: grid; grid-template-columns: 1fr 1fr; gap: 24px 40px; }
.author-copy p { margin: 0; color: rgb(241 239 232 / .72); font-size: 13px; line-height: 1.9; }
.author-signoff { margin: 65px 0 0; padding-top: 24px; border-top: 1px solid rgb(241 239 232 / .18); font: italic 600 clamp(18px, 2.2vw, 30px) 'Playfair Display', serif; }
.about-footer { padding-inline: max(32px, calc((100vw - 1240px) / 2)); width: 100%; }

@media (max-width: 1000px) {
  .space-grid { grid-template-columns: 1fr 1fr; }
  .origin-section { grid-template-columns: 150px 1fr; }
  .origin-copy { grid-column: 2; }
  .architecture-flow { grid-template-columns: 1fr; }
  .architecture-flow > i { transform: rotate(90deg); justify-self: center; }
  .author-copy { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .about-header,.about-hero,.origin-section,.spaces-section,.architecture-section { width: min(100% - 36px, 1240px); }
  .about-header nav > a:first-child { display: none; }
  .about-hero { display: block; min-height: auto; padding: 55px 0 75px; }
  .about-hero h1 { margin-top: 90px; font-size: clamp(55px, 17vw, 92px); }
  .hero-note { margin: 65px 0 0; }
  .origin-section { display: block; }
  .origin-section blockquote { margin: 65px 0; }
  .space-grid { grid-template-columns: 1fr; }
  .space-grid article { min-height: 350px; }
  .section-heading { display: block; }
  .section-heading > p { width: auto; margin-top: 25px; }
  .author-section { grid-template-columns: 1fr; }
  .author-aside { min-height: 280px; border-right: 0; border-bottom: 1px solid rgb(241 239 232 / .16); }
  .author-aside :deep(.brand-mark) { align-self: end; }
  .author-section article { padding: 70px 24px; }
  .about-footer { padding-inline: 18px; }
}

@media (prefers-reduced-motion: reduce) {
  .space-grid a b { transition: none; }
}
</style>
