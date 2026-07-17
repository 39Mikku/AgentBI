<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ProjectFooter from '@/components/brand/ProjectFooter.vue'

const router = useRouter()
const phrases: readonly [string, string, string] = [
  '把执行交给智能体。',
  '把协作交给系统。',
  '把灵感变成进展。',
]
const typedPhrase = ref('')
let phraseIndex = 0
let isDeleting = false
let typeTimer: ReturnType<typeof setTimeout> | undefined

function openLogin() {
  void router.push('/login')
}

function typeNextCharacter() {
  const phrase = phrases[phraseIndex] ?? phrases[0]
  typedPhrase.value = isDeleting
    ? phrase.slice(0, Math.max(0, typedPhrase.value.length - 1))
    : phrase.slice(0, typedPhrase.value.length + 1)

  let delay = isDeleting ? 45 : 92
  if (!isDeleting && typedPhrase.value === phrase) {
    isDeleting = true
    delay = 1800
  } else if (isDeleting && typedPhrase.value === '') {
    isDeleting = false
    phraseIndex = (phraseIndex + 1) % phrases.length
    delay = 360
  }
  typeTimer = setTimeout(typeNextCharacter, delay)
}

onMounted(typeNextCharacter)
onBeforeUnmount(() => clearTimeout(typeTimer))
</script>

<template>
  <main class="landing">
    <div class="landing-grain" aria-hidden="true"></div>
    <header class="site-header">
      <button class="wordmark" type="button" aria-label="AgentBI 首页" @click="router.push('/')">
        <span class="wordmark-mark" aria-hidden="true">
          <svg viewBox="0 0 34 34" fill="none">
            <path
              d="M17 3.4 29.2 10v14L17 30.6 4.8 24V10L17 3.4Z"
              stroke="currentColor"
              stroke-width="1.55"
            />
            <path
              d="m4.8 10 12.2 7 12.2-7M17 17v13.6"
              stroke="currentColor"
              stroke-width="1.2"
              opacity=".58"
            />
            <circle cx="17" cy="17" r="2.7" fill="currentColor" />
          </svg>
        </span>
        <span>AgentBI</span>
      </button>

      <nav class="site-nav" aria-label="主导航">
        <a href="#capabilities">能力</a>
        <a href="#workflow">工作方式</a>
        <button class="login-button" type="button" @click="openLogin">
          <span>登录</span><span aria-hidden="true">↗</span>
        </button>
      </nav>
    </header>

    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow"><i></i> MULTI-AGENT INTELLIGENCE / 01</p>
        <h1>
          把思考留给人，<br /><em
            >{{ typedPhrase }}<span class="typing-cursor" aria-hidden="true"></span
          ></em>
        </h1>
        <p class="hero-description">
          AgentBI
          将对话、上下文、模型与专业能力组织为一处干净的工作台。由你发问，由合适的智能体完成下一步。
        </p>
        <div class="hero-actions">
          <button class="primary-action" type="button" @click="openLogin">
            开始使用 <span aria-hidden="true">→</span>
          </button>
          <a class="text-action" href="#workflow"
            >看看它如何工作 <span aria-hidden="true">↓</span></a
          >
        </div>
        <blockquote>
          <span>“Give people wonderful tools, and they'll do wonderful things.”</span>
          <cite>— Apple</cite>
        </blockquote>
      </div>

      <div class="hero-stage" aria-label="AgentBI 对话工作台预览">
        <div class="orb orb-one" aria-hidden="true"></div>
        <div class="orb orb-two" aria-hidden="true"></div>
        <div class="console-card">
          <div class="console-topbar">
            <span class="console-dot"></span><span>NOW PROCESSING</span><time>09:41:22</time>
          </div>
          <div class="console-body">
            <div class="console-rail">
              <span class="rail-logo">A</span>
              <i></i><i></i><i></i>
              <b></b>
            </div>
            <div class="console-main">
              <div class="conversation-title">
                <span>项目智能助手</span><small>DEEPSEEK-V4</small>
              </div>
              <div class="message user-message">
                <span class="avatar human">Y</span>
                <p>整理本周的客户反馈，并生成需要跟进的事项。</p>
              </div>
              <div class="message agent-message">
                <span class="avatar agent">✦</span>
                <div>
                  <p>我会先归纳反馈中的主题，再让邮件智能体准备后续沟通。</p>
                  <div class="tool-event">
                    <i></i><span>已调用</span><strong>反馈分析 · 邮件智能体</strong>
                  </div>
                  <div class="reply-lines"><span></span><span></span><span></span></div>
                </div>
              </div>
              <div class="prompt-line"><span>询问任何事…</span><b>↑</b></div>
            </div>
          </div>
        </div>
        <div class="floating-card card-model">
          <span>◉</span>
          <div><small>已连接</small><b>多模型工作流</b></div>
        </div>
        <div class="floating-card card-memory">
          <span>⌁</span>
          <div><small>上下文</small><b>长期记忆已就绪</b></div>
        </div>
      </div>
    </section>

    <section id="capabilities" class="capabilities">
      <div class="section-intro">
        <p class="eyebrow"><i></i> DESIGNED FOR MOMENTUM / 02</p>
        <h2>一个入口，<br />一套会持续变得更懂你的系统。</h2>
      </div>
      <div class="capability-grid">
        <article>
          <span class="card-index">01</span>
          <div class="capability-symbol">◌</div>
          <h3>连续的对话</h3>
          <p>流式回复、思维摘要与可控上下文，让每一次提问自然延续。</p>
        </article>
        <article>
          <span class="card-index">02</span>
          <div class="capability-symbol">↗</div>
          <h3>专业的执行</h3>
          <p>通过子智能体承接邮件、数据和更多业务模块，主对话始终清晰。</p>
        </article>
        <article>
          <span class="card-index">03</span>
          <div class="capability-symbol">✦</div>
          <h3>灵活的选择</h3>
          <p>按助手切换模型、工具与工作方式，给不同场景恰到好处的能力。</p>
        </article>
      </div>
    </section>

    <section id="workflow" class="workflow">
      <div class="workflow-number">03</div>
      <div class="workflow-copy">
        <p class="eyebrow"><i></i> FROM PROMPT TO PROGRESS</p>
        <h2>说清你的目标。<br /><span>余下的交给系统。</span></h2>
      </div>
      <ol>
        <li>
          <span>01</span>
          <p>发起对话</p>
          <small>以自然语言描述你要完成的事。</small>
        </li>
        <li>
          <span>02</span>
          <p>智能编排</p>
          <small>主助手判断上下文与应当调用的专业能力。</small>
        </li>
        <li>
          <span>03</span>
          <p>获得结果</p>
          <small>结果、过程与后续动作清晰呈现在一条时间线上。</small>
        </li>
      </ol>
    </section>

    <ProjectFooter class="site-footer" />
  </main>
</template>

<style scoped>
.landing {
  --ink: #15191b;
  --paper: #f2f0e9;
  --acid: #c8fa43;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: var(--paper);
  color: var(--ink);
}
.landing-grain {
  position: fixed;
  z-index: 6;
  inset: 0;
  pointer-events: none;
  opacity: 0.16;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.26'/%3E%3C/svg%3E");
}
.site-header,
.hero,
.capabilities,
.workflow,
.site-footer {
  position: relative;
  z-index: 1;
}
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(1360px, calc(100% - 64px));
  margin: 0 auto;
  padding: 26px 0;
}
.wordmark,
.site-nav,
.login-button,
.hero-actions,
.eyebrow,
.console-topbar,
.tool-event,
.site-footer {
  font-family: var(--font-mono);
}
.wordmark {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  border: 0;
  background: none;
  color: var(--ink);
  font: 800 17px var(--font-display);
  letter-spacing: -0.05em;
  cursor: pointer;
}
.wordmark-mark {
  width: 28px;
  height: 28px;
  color: #fff;
  padding: 3px;
  border-radius: 8px;
  background: var(--ink);
}
.wordmark-mark svg {
  display: block;
  width: 100%;
  height: 100%;
}
.site-nav {
  display: flex;
  align-items: center;
  gap: 26px;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.site-nav > a {
  color: #5e625e;
  transition: color 0.2s ease;
}
.site-nav > a:hover {
  color: var(--ink);
}
.login-button {
  display: inline-flex;
  align-items: center;
  gap: 18px;
  padding: 10px 13px 10px 16px;
  border: 1px solid var(--ink);
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 10px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    background 0.2s ease,
    color 0.2s ease;
}
.login-button span:last-child {
  display: grid;
  width: 19px;
  height: 19px;
  place-items: center;
  border-radius: 50%;
  background: var(--acid);
  color: var(--ink);
  font-size: 13px;
}
.login-button:hover {
  background: transparent;
  color: var(--ink);
  transform: translateY(-2px);
}
.hero {
  display: grid;
  grid-template-columns: minmax(0, 0.91fr) minmax(560px, 1.09fr);
  gap: clamp(30px, 6vw, 110px);
  width: min(1240px, calc(100% - 64px));
  min-height: 670px;
  margin: 38px auto 96px;
  align-items: center;
}
.hero-copy {
  padding-bottom: 10px;
  animation: rise 0.8s cubic-bezier(0.2, 0.75, 0.2, 1) both;
}
.eyebrow {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 20px;
  color: #747870;
  font-size: 10px;
  letter-spacing: 0.12em;
}
.eyebrow i {
  width: 19px;
  height: 1px;
  background: var(--ink);
}
h1,
h2,
h3,
p,
blockquote {
  margin: 0;
}
h1 {
  max-width: 620px;
  font: 700 clamp(46px, 5.2vw, 78px)/0.97 var(--font-display);
  letter-spacing: -0.075em;
}
h1 em {
  font-weight: 500;
  font-style: normal;
  color: #90958c;
}
.typing-cursor {
  display: inline-block;
  width: 0.045em;
  height: 0.78em;
  margin: 0 0.02em 0 0.08em;
  vertical-align: -0.05em;
  background: var(--ink);
  animation: cursor-blink 820ms steps(1, end) infinite;
}
.hero-description {
  max-width: 490px;
  margin-top: 27px;
  color: #5e635e;
  font-size: 16px;
  line-height: 1.7;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 34px;
  font-size: 11px;
  letter-spacing: 0.04em;
}
.primary-action {
  display: inline-flex;
  align-items: center;
  gap: 28px;
  padding: 14px 15px 14px 21px;
  border: 0;
  border-radius: 3px;
  background: var(--acid);
  color: var(--ink);
  font: 700 11px var(--font-mono);
  cursor: pointer;
  box-shadow: 4px 4px 0 var(--ink);
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease;
}
.primary-action span {
  font-size: 18px;
  line-height: 10px;
}
.primary-action:hover {
  box-shadow: 1px 1px 0 var(--ink);
  transform: translate(3px, 3px);
}
.text-action {
  border-bottom: 1px solid #a3a69f;
  padding-bottom: 4px;
  color: #484d49;
}
.text-action:hover {
  color: var(--ink);
  border-color: var(--ink);
}
blockquote {
  display: grid;
  gap: 5px;
  max-width: 420px;
  margin-top: 77px;
  padding-left: 14px;
  border-left: 2px solid var(--acid);
  color: #545954;
  font-size: 12px;
  line-height: 1.6;
}
blockquote cite {
  color: #999c95;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.hero-stage {
  position: relative;
  height: 530px;
  animation: rise 0.9s 0.12s cubic-bezier(0.2, 0.75, 0.2, 1) both;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(1px);
}
.orb-one {
  top: 5%;
  right: -14%;
  width: 430px;
  height: 430px;
  background: radial-gradient(circle at 38% 38%, #dcff7d, #badf62 32%, #839e59 63%, #f2f0e9 69%);
  opacity: 0.72;
  animation: float 9s ease-in-out infinite;
}
.orb-two {
  bottom: -2%;
  left: 1%;
  width: 170px;
  height: 170px;
  border: 1px solid rgb(21 25 27 / 0.14);
  background: radial-gradient(
    circle at 50% 50%,
    transparent 42%,
    rgb(200 250 67 / 0.55) 43%,
    transparent 48%
  );
  animation: float 12s -3s ease-in-out infinite reverse;
}
.console-card {
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  width: min(596px, 96%);
  overflow: hidden;
  border: 1px solid #252a27;
  border-radius: 4px;
  background: #fcfcf9;
  box-shadow:
    18px 22px 0 rgb(21 25 27 / 0.11),
    0 26px 58px rgb(53 71 33 / 0.19);
  transform: translate(-50%, -47%) rotate(-2.2deg);
}
.console-topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 35px;
  padding: 0 13px;
  border-bottom: 1px solid #dadbd6;
  color: #777b74;
  font-size: 8px;
  letter-spacing: 0.09em;
}
.console-topbar time {
  margin-left: auto;
  color: #a4a69f;
}
.console-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--acid);
  box-shadow: 0 0 0 3px #edf5d2;
}
.console-body {
  display: grid;
  grid-template-columns: 51px 1fr;
  min-height: 360px;
}
.console-rail {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 17px;
  padding: 13px 0;
  border-right: 1px solid #e6e6e1;
  background: #f5f5f0;
}
.rail-logo {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  margin-bottom: 11px;
  border-radius: 7px;
  background: var(--ink);
  color: var(--acid);
  font: 700 12px var(--font-display);
}
.console-rail i {
  width: 16px;
  height: 2px;
  border-radius: 2px;
  background: #bfc1bb;
}
.console-rail i:nth-child(3) {
  background: #3b403c;
}
.console-rail b {
  width: 18px;
  height: 18px;
  margin-top: auto;
  border: 1px solid #bcbeb9;
  border-radius: 50%;
}
.console-main {
  padding: 21px 23px 17px;
}
.conversation-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 17px;
  border-bottom: 1px solid #eeeeea;
  color: #292e2a;
  font: 700 12px var(--font-display);
}
.conversation-title small {
  color: #93968e;
  font: 8px var(--font-mono);
  letter-spacing: 0.08em;
}
.message {
  display: flex;
  gap: 9px;
  margin-top: 19px;
  color: #363b36;
  font-size: 11px;
  line-height: 1.6;
}
.message p {
  max-width: 345px;
}
.avatar {
  display: grid;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  place-items: center;
  border-radius: 6px;
  font: 700 8px var(--font-mono);
}
.human {
  border: 1px solid #c6c9c1;
  color: #666a63;
}
.agent {
  background: var(--ink);
  color: var(--acid);
}
.tool-event {
  display: flex;
  align-items: center;
  gap: 5px;
  width: fit-content;
  margin: 12px 0;
  padding: 5px 7px;
  border: 1px solid #d9dfcb;
  background: #f6faeb;
  color: #7c8669;
  font-size: 8px;
  letter-spacing: 0.02em;
}
.tool-event i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #a2ce31;
}
.tool-event strong {
  color: #4d583c;
  font-weight: 500;
}
.reply-lines {
  display: grid;
  gap: 6px;
}
.reply-lines span {
  display: block;
  height: 5px;
  border-radius: 2px;
  background: #e5e7e1;
}
.reply-lines span:nth-child(1) {
  width: 93%;
}
.reply-lines span:nth-child(2) {
  width: 78%;
}
.reply-lines span:nth-child(3) {
  width: 58%;
}
.prompt-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 25px;
  padding: 10px 9px 10px 12px;
  border: 1px solid #e0e1db;
  border-radius: 4px;
  color: #a8aaa3;
  font-size: 9px;
}
.prompt-line b {
  display: grid;
  width: 16px;
  height: 16px;
  place-items: center;
  border-radius: 3px;
  background: var(--ink);
  color: #fff;
  font-size: 11px;
}
.floating-card {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 13px;
  border: 1px solid rgb(21 25 27 / 0.14);
  border-radius: 3px;
  background: rgb(252 252 249 / 0.92);
  box-shadow: 7px 8px 18px rgb(21 25 27 / 0.1);
  backdrop-filter: blur(8px);
  animation: float 7s ease-in-out infinite;
}
.floating-card > span {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 5px;
  background: #e8f9bd;
  color: #52692a;
  font-size: 12px;
}
.floating-card div {
  display: grid;
  gap: 1px;
}
.floating-card small {
  color: #91948d;
  font: 8px var(--font-mono);
}
.floating-card b {
  color: #3d423e;
  font: 700 9px var(--font-mono);
}
.card-model {
  top: 4%;
  left: -3%;
}
.card-memory {
  right: -1%;
  bottom: 3%;
  animation-delay: -3s;
}
.card-memory > span {
  background: #e5e7e1;
  color: #626861;
}
.capabilities {
  display: grid;
  grid-template-columns: 0.75fr 1.25fr;
  gap: 70px;
  width: min(1240px, calc(100% - 64px));
  margin: 0 auto;
  padding: 110px 0 120px;
  border-top: 1px solid #cbcdc5;
}
.section-intro h2,
.workflow h2 {
  font: 600 clamp(35px, 4vw, 56px)/1.02 var(--font-display);
  letter-spacing: -0.065em;
}
.section-intro h2 {
  max-width: 480px;
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: #c9cbc4;
  border: 1px solid #c9cbc4;
}
.capability-grid article {
  min-height: 300px;
  padding: 20px;
  background: var(--paper);
  transition:
    background 0.25s ease,
    transform 0.25s ease;
}
.capability-grid article:hover {
  background: #e7edda;
  transform: translateY(-5px);
}
.card-index {
  color: #92968e;
  font: 9px var(--font-mono);
}
.capability-symbol {
  margin: 70px 0 21px;
  color: #2c342b;
  font: 34px/1 var(--font-display);
}
.capability-grid h3 {
  font: 700 16px var(--font-display);
  letter-spacing: -0.04em;
}
.capability-grid p {
  margin-top: 8px;
  color: #6b7069;
  font-size: 12px;
  line-height: 1.65;
}
.workflow {
  display: grid;
  grid-template-columns: 120px 0.8fr 1.2fr;
  gap: 36px;
  padding: 100px max(32px, calc((100vw - 1240px) / 2));
  background: var(--ink);
  color: #f3f2eb;
}
.workflow-number {
  color: var(--acid);
  font: 11px var(--font-mono);
}
.workflow h2 span {
  color: #878d84;
}
.workflow ol {
  display: grid;
  gap: 19px;
  list-style: none;
}
.workflow li {
  display: grid;
  grid-template-columns: 43px 135px 1fr;
  gap: 10px;
  align-items: baseline;
  padding-bottom: 17px;
  border-bottom: 1px solid #353b36;
}
.workflow li span {
  color: var(--acid);
  font: 9px var(--font-mono);
}
.workflow li p {
  font: 600 14px var(--font-display);
  letter-spacing: -0.03em;
}
.workflow li small {
  color: #9ba199;
  font-size: 11px;
  line-height: 1.55;
}
.site-footer {
  width: min(1240px, calc(100% - 64px));
  margin: 0 auto;
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}
@keyframes cursor-blink {
  0%,
  48% {
    opacity: 1;
  }
  49%,
  100% {
    opacity: 0;
  }
}
@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
    margin-top: 55px;
  }
  .hero-stage {
    width: min(640px, 100%);
    justify-self: center;
  }
  .capabilities {
    grid-template-columns: 1fr;
  }
  .capability-grid {
    max-width: 720px;
  }
  .workflow {
    grid-template-columns: 75px 1fr;
  }
  .workflow ol {
    grid-column: 2;
  }
  .workflow-copy {
    grid-column: 2;
    grid-row: 1;
  }
}
@media (max-width: 650px) {
  .site-header,
  .hero,
  .capabilities,
  .site-footer {
    width: min(100% - 36px, 1240px);
  }
  .site-nav > a {
    display: none;
  }
  .site-nav {
    gap: 0;
  }
  .hero {
    min-height: 0;
    margin: 38px auto 70px;
  }
  .hero-stage {
    height: 370px;
  }
  .console-card {
    transform: translate(-50%, -47%) rotate(-2deg) scale(0.78);
  }
  .floating-card {
    transform: scale(0.8);
  }
  .card-model {
    left: -10%;
  }
  .card-memory {
    right: -10%;
  }
  .hero-description {
    font-size: 14px;
  }
  blockquote {
    margin-top: 44px;
  }
  .capability-grid {
    grid-template-columns: 1fr;
  }
  .capability-grid article {
    min-height: 0;
  }
  .capability-symbol {
    margin: 35px 0 17px;
  }
  .workflow {
    grid-template-columns: 1fr;
    gap: 24px;
    padding: 62px 18px;
  }
  .workflow-copy,
  .workflow ol {
    grid-column: auto;
    grid-row: auto;
  }
  .workflow li {
    grid-template-columns: 34px 1fr;
  }
  .workflow li small {
    grid-column: 2;
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
