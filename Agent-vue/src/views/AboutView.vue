<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/')
}

interface Capability {
  name: string
  desc: string
  tag: string
  status: 'online' | 'ready'
  glyph: string
}

const capabilities: Capability[] = [
  {
    name: '邮件智能投递',
    desc: 'LangChain @tool 装配的邮件发送工具，由大模型自主决策收件人与内容。',
    tag: 'send_email_tool',
    status: 'online',
    glyph: 'mail',
  },
  {
    name: '数据库实时查询',
    desc: 'MongoDB 查询工具，将自然语言意图转化为精确的字段级查询体。',
    tag: 'mongo_query_tool',
    status: 'online',
    glyph: 'db',
  },
  {
    name: '上下文持久记忆',
    desc: 'MemorySaver 检查点挂载，跨轮次会话通过 thread_id 保持记忆连续性。',
    tag: 'MemorySaver',
    status: 'ready',
    glyph: 'brain',
  },
  {
    name: '强类型契约校验',
    desc: 'Pydantic Schema 双向约束入参与出参，杜绝大模型字段漂移。',
    tag: 'schemas/',
    status: 'ready',
    glyph: 'shield',
  },
]

const glyphs: Record<string, string> = {
  mail: 'M3 7l9 6 9-6M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
  db: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  brain: 'M9.5 4a2.5 2.5 0 0 0-2.5 2.5v.2A2.5 2.5 0 0 0 5 9.2c0 1 .6 1.9 1.5 2.3-.6.5-1 1.2-1 2 0 1.4 1.1 2.5 2.5 2.5h.5M14.5 4A2.5 2.5 0 0 1 17 6.5v.2a2.5 2.5 0 0 1 2 2.5c0 1-.6 1.9-1.5 2.3.6.5 1 1.2 1 2 0 1.4-1.1 2.5-2.5 2.5H16M9.5 4h5M9.5 16h5M12 4v12',
  shield: 'M12 3l7 3v5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6l7-3z',
}
</script>

<template>
  <div class="console">
    <header class="console-bar">
      <div class="bar-brand">
        <span class="bar-dot"></span>
        <span class="bar-name">AgentBI</span>
        <span class="bar-sep">/</span>
        <span class="bar-crumb">控制台</span>
      </div>
      <div class="bar-actions">
        <ThemeToggle />
        <button class="btn-ghost" type="button" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M15 17l5-5-5-5M20 12H9M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          </svg>
          <span>退出登录</span>
        </button>
      </div>
    </header>

    <main class="console-main">
      <section class="welcome" style="animation: fade-up 0.6s ease both">
        <p class="welcome-eyebrow">访问已授权</p>
        <h1 class="welcome-title">
          欢迎回来<span class="title-dot">.</span>
        </h1>
        <p class="welcome-sub">
          身份核验通过，智能体中枢已就绪。当前会话由邮箱验证码通道建立，
          <span class="mono">{{ auth.email || '已认证用户' }}</span> 拥有完整工具调用权限。
        </p>
      </section>

      <section class="cap-grid">
        <h2 class="grid-heading" style="animation: fade-up 0.6s ease 0.1s both">
          <span class="heading-index">01</span>
          智能体能力矩阵
        </h2>
        <div class="cards">
          <article
            v-for="(cap, i) in capabilities"
            :key="cap.name"
            class="cap-card"
            :style="{ animationDelay: `${0.15 + i * 0.08}s` }"
          >
            <div class="cap-head">
              <span class="cap-glyph">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path :d="glyphs[cap.glyph]" />
                </svg>
              </span>
              <span class="cap-status" :class="cap.status">
                <i class="status-dot"></i>
                {{ cap.status === 'online' ? '运行中' : '就绪' }}
              </span>
            </div>
            <h3 class="cap-name">{{ cap.name }}</h3>
            <p class="cap-desc">{{ cap.desc }}</p>
            <code class="cap-tag">{{ cap.tag }}</code>
          </article>
        </div>
      </section>

      <section class="arch-note" style="animation: fade-up 0.6s ease 0.5s both">
        <div class="note-glyph">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" />
          </svg>
        </div>
        <div class="note-body">
          <p class="note-title">架构备忘</p>
          <p class="note-text">
            后端基于 FastAPI + LangChain 构建，以 OOP 封装的 <span class="mono">LoginAgent</span> 为大脑，
            通过 <span class="mono">@tool</span> 装配本地工具集。验证码经 Redis 缓存（TTL 300s）双向绑定，
            登录校验在服务端完成。
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.console {
  min-height: 100vh;
  background: var(--background);
  color: var(--foreground);
}

/* ---- top bar ---- */
.console-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(1.2rem, 4vw, 3rem);
  height: 64px;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--background) 82%, transparent);
  backdrop-filter: saturate(180%) blur(18px);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
}
.bar-brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}
.bar-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--success) 22%, transparent);
  animation: pulse-ring 3s ease-in-out infinite;
}
.bar-name {
  color: var(--foreground);
}
.bar-sep {
  color: var(--muted-foreground);
  font-weight: 400;
}
.bar-crumb {
  color: var(--muted-foreground);
  font-weight: 500;
}
.bar-actions {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  height: 42px;
  padding: 0 1.1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--card);
  color: var(--foreground);
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.86rem;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}
.btn-ghost svg {
  width: 17px;
  height: 17px;
}
.btn-ghost:hover {
  border-color: var(--destructive);
  color: var(--destructive);
  transform: translateY(-1px);
}

/* ---- main ---- */
.console-main {
  max-width: 1080px;
  margin: 0 auto;
  padding: clamp(2rem, 5vw, 4rem) clamp(1.2rem, 4vw, 3rem) 4rem;
}

.welcome-eyebrow {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--success);
  margin-bottom: 0.9rem;
}
.welcome-title {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  line-height: 1.05;
  letter-spacing: -0.02em;
}
.title-dot {
  color: var(--primary);
}
.welcome-sub {
  margin-top: 1rem;
  max-width: 56ch;
  color: var(--muted-foreground);
  font-size: 1.02rem;
  line-height: 1.65;
}
.mono {
  font-family: var(--font-mono);
  font-size: 0.88em;
  color: var(--foreground);
  background: var(--muted);
  padding: 0.1em 0.45em;
  border-radius: 0.4rem;
}

/* ---- capability grid ---- */
.grid-heading {
  display: flex;
  align-items: baseline;
  gap: 0.9rem;
  margin: 3.5rem 0 1.6rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.3rem;
  letter-spacing: -0.01em;
}
.heading-index {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--primary);
  letter-spacing: 0.1em;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}
.cap-card {
  padding: 1.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  animation: fade-up 0.55s ease both;
  transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
}
.cap-card:hover {
  border-color: color-mix(in srgb, var(--primary) 50%, var(--border));
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
.cap-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.1rem;
}
.cap-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 0.8rem;
  background: color-mix(in srgb, var(--primary) 12%, var(--card));
  color: var(--primary);
}
.cap-glyph svg {
  width: 21px;
  height: 21px;
}
.cap-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: var(--muted-foreground);
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted-foreground);
}
.cap-status.online .status-dot {
  background: var(--success);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--success) 20%, transparent);
}
.cap-status.online {
  color: var(--success);
}
.cap-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.12rem;
  letter-spacing: -0.01em;
  margin-bottom: 0.5rem;
}
.cap-desc {
  color: var(--muted-foreground);
  font-size: 0.9rem;
  line-height: 1.6;
  margin-bottom: 1.1rem;
}
.cap-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
  padding: 0.25rem 0.6rem;
  border-radius: 0.5rem;
}

/* ---- arch note ---- */
.arch-note {
  display: flex;
  gap: 1.2rem;
  margin-top: 3rem;
  padding: 1.6rem;
  border: 1px solid var(--border);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--primary) 4%, var(--card));
}
.note-glyph {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 0.7rem;
  background: var(--card);
  color: var(--primary);
  box-shadow: var(--shadow-xs);
}
.note-glyph svg {
  width: 19px;
  height: 19px;
  animation: spin 16s linear infinite;
}
.note-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.98rem;
  margin-bottom: 0.35rem;
}
.note-text {
  color: var(--muted-foreground);
  font-size: 0.9rem;
  line-height: 1.65;
}

@media (max-width: 640px) {
  .btn-ghost span {
    display: none;
  }
  .arch-note {
    flex-direction: column;
  }
}
</style>
