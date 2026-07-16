<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAssistants } from '@/api/assistants'
import { listConversations } from '@/api/chat'
import { formatRelativeTime } from '@/home/home-time'
import { mergeRecentConversations, type RecentConversation } from '@/home/home-recent'

const props = defineProps<{ userId: string }>()
const recent = ref<RecentConversation[]>([])
const loading = ref(true)

async function loadRecent() {
  loading.value = true
  try {
    const assistants = await listAssistants(props.userId)
    if (!assistants.length) {
      recent.value = mergeRecentConversations([], await listConversations(props.userId))
      return
    }
    const results = await Promise.allSettled(
      assistants.map((assistant) => listConversations(props.userId, assistant.id)),
    )
    const conversations = results.flatMap((result) =>
      result.status === 'fulfilled' ? result.value : [],
    )
    recent.value = mergeRecentConversations(assistants, conversations)
  } catch {
    try {
      recent.value = mergeRecentConversations([], await listConversations(props.userId))
    } catch {
      recent.value = []
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadRecent)
</script>

<template>
  <section class="recent-panel" aria-labelledby="recent-title">
    <header>
      <div>
        <span>CONTINUE / STUDIO</span>
        <h2 id="recent-title">最近会话</h2>
      </div>
      <RouterLink to="/chat">全部会话 ↗</RouterLink>
    </header>

    <div v-if="loading" class="recent-loading" aria-label="正在加载最近会话">
      <i v-for="n in 3" :key="n"></i>
    </div>
    <ol v-else-if="recent.length" class="recent-list">
      <li v-for="(conversation, index) in recent" :key="conversation.id">
        <RouterLink :to="conversation.href">
          <span class="recent-number">0{{ index + 1 }}</span>
          <div>
            <strong>{{ conversation.title }}</strong>
            <small>
              <template v-if="conversation.assistantName">{{ conversation.assistantName }} · </template>
              {{ formatRelativeTime(conversation.activityAt) || '历史会话' }}
            </small>
          </div>
          <b>→</b>
        </RouterLink>
      </li>
    </ol>
    <div v-else class="recent-empty">
      <p>这里还没有可继续的对话。</p>
      <RouterLink to="/chat">开始第一段会话 →</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.recent-panel { border-top: 1px solid #cac5b9; padding-top: 20px; color: #171713; }
.recent-panel header { display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 22px; }
.recent-panel header span { display: block; margin-bottom: 5px; color: #767269; font: 500 8px 'DM Mono', monospace; letter-spacing: .16em; }
.recent-panel h2 { font: 600 clamp(26px,3vw,42px)/1 'Playfair Display', serif; letter-spacing: -.04em; }
.recent-panel header > a { font: 500 9px 'DM Mono', monospace; border-bottom: 1px solid currentColor; padding-bottom: 3px; }
.recent-list { list-style: none; }
.recent-list li { border-top: 1px solid #cac5b9; }
.recent-list li:last-child { border-bottom: 1px solid #cac5b9; }
.recent-list a { display: grid; grid-template-columns: 42px 1fr auto; align-items: center; gap: 12px; min-height: 72px; padding: 10px 2px; transition: padding .25s, background .25s; }
.recent-list a:hover, .recent-list a:focus-visible { padding-inline: 12px; background: rgba(17,17,15,.045); outline: none; }
.recent-number { color: #89857c; font: 9px 'DM Mono', monospace; }
.recent-list strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; font-weight: 650; }
.recent-list small { display: block; margin-top: 4px; color: #7c786f; font: 8px 'DM Mono', monospace; }
.recent-list b { font-size: 18px; font-weight: 400; transition: transform .25s; }
.recent-list a:hover b { transform: translateX(5px); }
.recent-loading { display: grid; gap: 1px; background: #cac5b9; }
.recent-loading i { display: block; height: 72px; background: linear-gradient(90deg,#e4e0d6 25%,#eeebe2 40%,#e4e0d6 60%); background-size: 300% 100%; animation: recent-shimmer 1.35s infinite; }
.recent-empty { min-height: 160px; display: grid; place-content: center; justify-items: center; gap: 10px; border-block: 1px solid #cac5b9; color: #77736b; font-size: 12px; }
.recent-empty a { color: #171713; font: 9px 'DM Mono', monospace; }
@keyframes recent-shimmer { to { background-position: -100% 0; } }
@media (prefers-reduced-motion: reduce) { .recent-loading i { animation: none; } }
</style>
