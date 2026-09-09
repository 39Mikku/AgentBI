<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import ProjectFooter from '@/components/brand/ProjectFooter.vue'
import HomeModuleEntry from '@/components/home/HomeModuleEntry.vue'
import HomeRecentConversations from '@/components/home/HomeRecentConversations.vue'
import quotes from '@/content/home-quotes.json'
import { initialQuoteIndex, nextQuoteIndex } from '@/home/home-quotes'
import { formatHomeDate, greetingForHour } from '@/home/home-time'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
const now = ref(new Date())
const quoteIndex = ref(initialQuoteIndex(quotes.length))
let clockTimer: ReturnType<typeof setInterval> | undefined
let quoteTimer: ReturnType<typeof setInterval> | undefined

const username = computed(() =>
  workspace.profile?.username?.trim() || workspace.userId.split('@')[0] || '探索者',
)
const initials = computed(() => username.value.slice(0, 2).toUpperCase())
const hour = computed(() => String(now.value.getHours()).padStart(2, '0'))
const minute = computed(() => String(now.value.getMinutes()).padStart(2, '0'))
const second = computed(() => String(now.value.getSeconds()).padStart(2, '0'))
const currentQuote = computed(() => quotes[quoteIndex.value] || quotes[0])

function startQuoteRotation() {
  if (quoteTimer || document.hidden) return
  quoteTimer = setInterval(() => {
    quoteIndex.value = nextQuoteIndex(quoteIndex.value, quotes.length)
  }, 10_000)
}

function stopQuoteRotation() {
  if (quoteTimer) clearInterval(quoteTimer)
  quoteTimer = undefined
}

function onVisibilityChange() {
  if (document.hidden) stopQuoteRotation()
  else startQuoteRotation()
}

onMounted(() => {
  clockTimer = setInterval(() => { now.value = new Date() }, 1_000)
  startQuoteRotation()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  if (clockTimer) clearInterval(clockTimer)
  stopQuoteRotation()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <main class="workspace-home">
    <div class="home-grain" aria-hidden="true"></div>
    <header class="home-nav home-reveal" style="--delay: 0s">
      <RouterLink class="home-brand" to="/home" aria-label="AgentBI 主页">
        <i></i>
        <strong>AGENTBI</strong>
        <span>/ DAILY BRIEFING</span>
      </RouterLink>
      <div class="nav-date">{{ formatHomeDate(now) }}</div>
      <div class="user-area">
        <RouterLink class="user-chip" to="/chat" title="进入 Studio">
          <span v-if="workspace.profile?.avatar_data_url" class="user-avatar image">
            <img :src="workspace.profile.avatar_data_url" alt="" />
          </span>
          <span v-else class="user-avatar">{{ initials }}</span>
          <span>{{ username }}</span>
        </RouterLink>
        <a class="project-link" href="https://agentbi.39miku.tech/" target="_blank" rel="noreferrer">官网 ↗</a>
      </div>
    </header>

    <section class="briefing-hero">
      <div class="hero-intro home-reveal" style="--delay: .06s">
        <p class="section-label">LOCAL DESK · {{ Intl.DateTimeFormat().resolvedOptions().timeZone }}</p>
        <h1>
          <span>{{ greetingForHour(now.getHours()) }}，</span>
          {{ username }}<em>。</em>
        </h1>
        <p class="hero-note">你的工作台已经就绪。选择一条路径，继续今天的创造。</p>
      </div>

      <div class="hero-clock home-reveal" style="--delay: .12s" aria-label="当前时间">
        <div><span>{{ hour }}</span><i>:</i><span>{{ minute }}</span><small>{{ second }}</small></div>
        <p>ASIA / SHANGHAI <b>LIVE</b></p>
      </div>

      <div class="quote-column home-reveal" style="--delay: .18s">
        <span class="quote-mark">“</span>
        <Transition name="quote" mode="out-in">
          <blockquote :key="quoteIndex">
            <p>{{ currentQuote?.text }}</p>
            <cite>— {{ currentQuote?.speaker }}</cite>
          </blockquote>
        </Transition>
        <div class="quote-progress">
          <i v-for="(_, index) in quotes" :key="index" :class="{ active: index === quoteIndex }"></i>
        </div>
      </div>
    </section>

    <section class="workspace-section">
      <header class="section-heading home-reveal" style="--delay: .22s">
        <span>01 / WORKSPACES</span>
        <p>四种工作方式，共用同一套本地身份与配置。</p>
      </header>
      <div class="module-grid home-reveal" style="--delay: .26s">
        <HomeModuleEntry
          index="01"
          title="Studio"
          description="完整上下文、助手、工具与多模态工作台"
          to="/chat"
          accent="#d9ff36"
          variant="hero"
        />
        <HomeModuleEntry
          index="02"
          title="Live"
          description="实时语音、角色与流式转写"
          to="/live"
          accent="#80f4db"
          variant="signal"
        />
        <HomeModuleEntry
          index="03"
          title="Test"
          description="知识测试与趣味测试实验室"
          to="/test"
          accent="#ff775e"
          variant="paper"
        />
        <HomeModuleEntry
          index="04"
          title="Playground"
          description="角色、世界书与长篇叙事空间"
          to="/playground"
          accent="#d7ff3f"
          variant="story"
        />
      </div>
    </section>

    <section class="lower-grid home-reveal" style="--delay: .32s">
      <HomeRecentConversations :user-id="workspace.userId" />
      <aside class="quick-panel">
        <header>
          <span>02 / QUICK ACCESS</span>
          <h2>控制面板</h2>
        </header>
        <nav aria-label="快捷设置">
          <RouterLink to="/toolbox"><span>工具箱</span><small>LOCAL UTILITIES</small><b>↗</b></RouterLink>
          <RouterLink to="/settings/models"><span>模型工作台</span><small>MODEL ROUTES</small><b>↗</b></RouterLink>
          <RouterLink to="/assistants"><span>助手管理</span><small>ASSISTANTS</small><b>↗</b></RouterLink>
          <RouterLink to="/attachments"><span>附件管理</span><small>ASSETS</small><b>↗</b></RouterLink>
          <RouterLink to="/settings/capabilities"><span>能力配置</span><small>TOOLS & AGENTS</small><b>↗</b></RouterLink>
        </nav>
      </aside>
    </section>

    <ProjectFooter class="home-footer" />
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.workspace-home {
  --ink: #12120f;
  --paper: #e8e4da;
  --paper-deep: #d8d3c7;
  --acid: #d9ff36;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding: 0 clamp(18px,4.8vw,76px) 34px;
  background: var(--paper);
  color: var(--ink);
  font-family: Manrope, sans-serif;
}
.home-grain { position: fixed; inset: 0; pointer-events: none; z-index: 20; opacity: .08; mix-blend-mode: multiply; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.35'/%3E%3C/svg%3E"); }
.home-nav { position: relative; z-index: 21; height: 74px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; border-bottom: 1px solid #bbb6aa; }
.home-brand { display: flex; align-items: center; gap: 9px; width: max-content; font: 500 10px 'DM Mono', monospace; letter-spacing: .12em; }
.home-brand i { width: 17px; height: 17px; position: relative; border: 1px solid var(--ink); }
.home-brand i::after { content: ''; position: absolute; width: 6px; height: 6px; right: -4px; bottom: -4px; background: var(--acid); border: 1px solid var(--ink); }
.home-brand span { color: #827e75; }
.nav-date { font: 9px 'DM Mono', monospace; letter-spacing: .08em; }
.user-area { justify-self: end; display: flex; align-items: center; gap: 13px; }
.user-chip { display: flex; align-items: center; gap: 8px; font-size: 10px; font-weight: 650; }
.user-avatar { display: grid; place-items: center; width: 30px; height: 30px; overflow: hidden; border: 1px solid var(--ink); background: var(--acid); font: 600 8px 'DM Mono', monospace; }
.user-avatar.image { background: #d7d3c9; }
.user-avatar img { width: 100%; height: 100%; object-fit: cover; }
.project-link { border: 0; border-left: 1px solid #bbb6aa; background: transparent; padding: 4px 0 4px 13px; color: #77736b; cursor: pointer; font: 8px 'DM Mono', monospace; }
.project-link:hover { color: var(--ink); }

.briefing-hero { min-height: 505px; display: grid; grid-template-columns: minmax(0,1.15fr) minmax(320px,.85fr); grid-template-rows: 1fr auto; column-gap: clamp(30px,6vw,100px); border-bottom: 1px solid #bbb6aa; padding: clamp(55px,8vw,108px) 0 42px; }
.section-label, .section-heading span, .quick-panel header span { color: #767269; font: 500 8px 'DM Mono', monospace; letter-spacing: .17em; }
.hero-intro h1 { max-width: 850px; margin: 22px 0 24px; font: 600 clamp(55px,8vw,120px)/.81 'Playfair Display', serif; letter-spacing: -.07em; }
.hero-intro h1 span { display: block; color: #77736b; font-style: italic; }
.hero-intro h1 em { color: #aacb1e; font-style: normal; }
.hero-note { max-width: 440px; color: #6e6a62; font-size: 12px; line-height: 1.75; }
.hero-clock { align-self: center; justify-self: end; width: min(100%,520px); border-top: 1px solid #aaa59a; padding-top: 13px; }
.hero-clock > div { display: flex; align-items: baseline; justify-content: flex-end; font: 600 clamp(65px,9vw,136px)/.8 Manrope, sans-serif; letter-spacing: -.095em; white-space: nowrap; }
.hero-clock i { color: #a3c326; font-style: normal; font-weight: 400; margin: 0 .03em; transform: translateY(-.08em); }
.hero-clock small { margin-left: 12px; color: #7b776e; font: 500 13px 'DM Mono', monospace; letter-spacing: 0; }
.hero-clock > p { display: flex; justify-content: space-between; margin-top: 16px; color: #77736b; font: 8px 'DM Mono', monospace; letter-spacing: .13em; }
.hero-clock b { color: #62720e; font-weight: 500; }
.hero-clock b::before { content: ''; display: inline-block; width: 5px; height: 5px; margin-right: 7px; border-radius: 50%; background: #95b310; box-shadow: 0 0 0 5px rgba(149,179,16,.12); }
.quote-column { grid-column: 2; min-height: 118px; align-self: end; position: relative; border-left: 3px solid var(--ink); padding-left: 22px; }
.quote-mark { position: absolute; right: 0; top: -26px; color: #cbc6ba; font: 100px/1 'Playfair Display', serif; }
.quote-column blockquote { position: relative; min-height: 75px; padding-right: 38px; }
.quote-column blockquote p { max-width: 480px; font: 600 clamp(16px,1.7vw,24px)/1.35 'Playfair Display', serif; letter-spacing: -.02em; }
.quote-column cite { display: block; margin-top: 12px; color: #77736b; font: 8px 'DM Mono', monospace; font-style: normal; letter-spacing: .1em; text-transform: uppercase; }
.quote-progress { display: flex; gap: 4px; margin-top: 10px; }
.quote-progress i { width: 16px; height: 2px; background: #b9b4a8; }
.quote-progress i.active { background: var(--ink); }
.quote-enter-active,.quote-leave-active { transition: opacity .35s, transform .35s; }
.quote-enter-from { opacity: 0; transform: translateY(8px); }
.quote-leave-to { opacity: 0; transform: translateY(-8px); }

.workspace-section { padding: 43px 0 66px; }
.section-heading { display: flex; justify-content: space-between; align-items: end; margin-bottom: 18px; }
.section-heading p { color: #77736b; font-size: 10px; }
.module-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1px; background: #34342f; border: 1px solid #34342f; }
.lower-grid { display: grid; grid-template-columns: minmax(0,1.35fr) minmax(300px,.65fr); gap: clamp(35px,6vw,100px); padding: 0 0 72px; }
.quick-panel { border-top: 1px solid #cac5b9; padding-top: 20px; }
.quick-panel h2 { margin-top: 5px; font: 600 clamp(26px,3vw,42px)/1 'Playfair Display', serif; letter-spacing: -.04em; }
.quick-panel nav { margin-top: 22px; border-top: 1px solid #cac5b9; }
.quick-panel a { display: grid; grid-template-columns: 1fr auto 20px; align-items: center; min-height: 58px; gap: 10px; border-bottom: 1px solid #cac5b9; transition: padding .25s, background .25s; }
.quick-panel a:hover,.quick-panel a:focus-visible { padding-inline: 10px; background: rgba(17,17,15,.045); outline: none; }
.quick-panel a span { font-size: 12px; font-weight: 650; }
.quick-panel a small { color: #827e75; font: 7px 'DM Mono', monospace; letter-spacing: .08em; }
.quick-panel a b { font-size: 13px; font-weight: 400; }
.home-footer { min-height: 96px; }
.home-reveal { opacity: 0; animation: home-reveal .65s cubic-bezier(.2,.75,.2,1) forwards; animation-delay: var(--delay); }
@keyframes home-reveal { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

@media (max-width: 1050px) {
  .briefing-hero { grid-template-columns: 1fr 320px; }
  .hero-intro h1 { font-size: clamp(54px,9vw,88px); }
  .module-grid { grid-template-columns: 1fr 1fr; }
  .lower-grid { grid-template-columns: 1fr 340px; }
}
@media (max-width: 820px) {
  .home-nav { grid-template-columns: 1fr auto; }
  .nav-date { display: none; }
  .briefing-hero { display: block; min-height: auto; padding-top: 62px; }
  .hero-clock { width: 100%; margin: 58px 0 48px; }
  .hero-clock > div { justify-content: flex-start; }
  .quote-column { min-height: 125px; }
  .module-grid { grid-template-columns: 1fr; }
  .lower-grid { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .workspace-home { padding-inline: 14px; }
  .home-brand span,.user-chip > span:last-child,.project-link { display: none; }
  .briefing-hero { padding-top: 48px; }
  .hero-intro h1 { font-size: clamp(49px,17vw,74px); }
  .hero-clock > div { font-size: clamp(58px,23vw,95px); }
  .hero-clock small { font-size: 10px; margin-left: 7px; }
  .section-heading { display: block; }
  .section-heading p { margin-top: 8px; }
}
@media (prefers-reduced-motion: reduce) {
  .home-reveal { opacity: 1; animation: none; }
  .quote-enter-active,.quote-leave-active { transition: none; }
}
</style>
