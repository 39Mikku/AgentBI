<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ModelAvatar from '@/components/ModelAvatar.vue'
import { getUserProfile, saveUserAvatar } from '@/api/user-profile'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { renderMarkdown } from '@/utils/markdown'
import { createRuntimeContext } from '@/utils/runtime-context'
import type { ChatMessage } from '@/api/chat-types'

const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const input = ref('')
const menuOpen = ref(false)
const profileOpen = ref(false)
const profileBusy = ref(false)
const profileError = ref('')
const profile = computed(() => auth.profile)
const editingId = ref('')
const editingTitle = ref('')
const editingMessageId = ref('')
const editingMessageContent = ref('')
const timeline = ref<HTMLElement | null>(null)
const previewTurn = ref(-1)
const userId = computed(() => auth.email || 'local-user')
const modelLabel = computed(() => chat.preferences.model || '选择模型')
const userName = computed(() => profile.value?.username || (userId.value.includes('@') ? userId.value.split('@')[0] || userId.value : userId.value))
const userInitials = computed(() => userName.value.slice(0, 2).toUpperCase())
const conversationTurns = computed(() => {
  const turns: Array<{ user?: ChatMessage; assistant?: ChatMessage }> = []
  for (const message of chat.messages) {
    if (message.role === 'user') {
      turns.push({ user: message })
      continue
    }
    const openTurn = turns.at(-1)
    if (openTurn && !openTurn.assistant) openTurn.assistant = message
    else turns.push({ assistant: message })
  }
  return turns
})

function previewText(message?: ChatMessage) {
  const content = message?.content?.replace(/\s+/g, ' ').trim()
  return content || (message?.status === 'streaming' ? '正在生成回复…' : '暂无内容')
}

function parseTimestamp(value?: string) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function isSameDay(left: Date, right: Date) {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth() && left.getDate() === right.getDate()
}

function formatClock(date: Date) {
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(date)
}

function formatMessageTime(value?: string) {
  const date = parseTimestamp(value)
  if (!date) return ''
  const now = new Date()
  if (isSameDay(date, now)) return formatClock(date)
  const datePart = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
  return `${datePart} ${formatClock(date)}`
}

function formatConversationDate(value?: string) {
  const date = parseTimestamp(value)
  if (!date) return ''
  const now = new Date()
  if (isSameDay(date, now)) return `今天 ${formatClock(date)}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (isSameDay(date, yesterday)) return `昨天 ${formatClock(date)}`
  if (date.getFullYear() === now.getFullYear()) return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'numeric', day: 'numeric' }).format(date)
}

function send() { const value = input.value.trim(); if (value) { input.value = ''; void chat.send(userId.value, value, createRuntimeContext(userName.value, navigator.language, Intl.DateTimeFormat().resolvedOptions().timeZone)) } }
function runtimeContext() { return createRuntimeContext(userName.value, navigator.language, Intl.DateTimeFormat().resolvedOptions().timeZone) }
function retryMessage(message: ChatMessage) { void chat.retry(userId.value, message.id, runtimeContext()) }
function beginMessageEdit(message: ChatMessage) { editingMessageId.value = message.id; editingMessageContent.value = message.content }
function cancelMessageEdit() { editingMessageId.value = ''; editingMessageContent.value = '' }
function saveMessageEdit(message: ChatMessage) {
  const content = editingMessageContent.value.trim()
  if (!content) return
  cancelMessageEdit()
  void chat.edit(userId.value, message.id, content, runtimeContext())
}
function selectVersion(message: ChatMessage, direction: -1 | 1) {
  const versions = message.version_ids || []
  if (!versions.length) return
  const next = (message.sibling_index || 0) + direction
  if (next < 0 || next >= versions.length) return
  const target = versions[next]
  if (target) void chat.selectVersion(userId.value, target)
}
function branchFrom(message: ChatMessage) { void chat.branch(userId.value, message.id) }
function keydown(event: KeyboardEvent) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }
async function newChat() { await chat.create(userId.value); menuOpen.value = false }
function logout() { auth.logout(); void router.push('/') }
function beginRename(id: string, title: string) { editingId.value = id; editingTitle.value = title }
function cancelRename() { editingId.value = ''; editingTitle.value = '' }
async function commitRename(id: string) {
  if (!editingTitle.value.trim()) return cancelRename()
  await chat.rename(id, userId.value, editingTitle.value)
  cancelRename()
}
async function loadProfile() {
  if (profile.value?.user_id === userId.value) return
  try { auth.setProfile(await getUserProfile(userId.value)) } catch (error) { profileError.value = error instanceof Error ? error.message : '无法读取用户资料' }
}
async function uploadAvatar(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { profileError.value = '请选择图片文件'; return }
  if (file.size > 1_400_000) { profileError.value = '头像请控制在 1.4 MB 以内'; return }
  profileBusy.value = true; profileError.value = ''
  try {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(new Error('读取图片失败'))
      reader.readAsDataURL(file)
    })
    auth.setProfile(await saveUserAvatar(userId.value, dataUrl))
  } catch (error) { profileError.value = error instanceof Error ? error.message : '头像保存失败' } finally { profileBusy.value = false }
}

watch(() => chat.messages.length, async () => { await nextTick(); timeline.value?.scrollTo({ top: timeline.value.scrollHeight, behavior: 'smooth' }) })
onMounted(async () => { await Promise.all([chat.load(userId.value), loadProfile()]) })
</script>

<template>
  <div class="workbench" :class="{ 'sidebar-open': menuOpen }">
    <aside class="rail">
      <div class="rail-brand"><span class="brand-orbit"></span><span>OBSIDIAN</span><i>AI</i></div>
      <button class="new-session" @click="newChat"><span>＋</span> 新建对话 <kbd>⌘ K</kbd></button>
      <div class="rail-label">会话档案</div>
      <nav class="conversation-list">
        <article v-for="item in chat.conversations" :key="item.id" class="conversation-row" :class="{ active: item.id === chat.activeId }">
          <button class="conversation-main" @click="chat.select(item.id, userId)">
            <span class="conversation-signal"></span>
            <input v-if="editingId === item.id" v-model="editingTitle" class="rename-input" maxlength="120" autofocus @click.stop @keydown.enter.prevent="commitRename(item.id)" @keydown.esc.prevent="cancelRename" @blur="commitRename(item.id)" />
            <span v-else class="conversation-copy"><span class="conversation-title">{{ item.title }}</span><time v-if="item.last_message_at || item.updated_at || item.created_at" class="conversation-date">{{ formatConversationDate(item.last_message_at || item.updated_at || item.created_at) }}</time></span>
          </button>
          <span class="conversation-actions">
            <button title="重命名" @click.stop="beginRename(item.id, item.title)">✎</button>
            <button title="删除" @click.stop="chat.remove(item.id, userId)">×</button>
          </span>
        </article>
        <p v-if="!chat.conversations.length && !chat.loading" class="empty-list">没有历史会话<br />从右侧开始一段思考。</p>
      </nav>
      <div class="rail-footer">
        <button class="user-card" @click="profileOpen = true">
          <img v-if="profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" />
          <span v-else class="user-initials">{{ userInitials }}</span>
          <span><strong>{{ userName }}</strong><small>{{ profile?.email || userId }}</small></span><b>›</b>
        </button>
        <button @click="router.push('/settings/models')">◈ 模型工作室</button>
        <button @click="logout">↗ 退出会话</button>
      </div>
    </aside>

    <main class="dialogue">
      <header class="dialogue-head">
        <button class="mobile-menu" @click="menuOpen = !menuOpen">☰</button>
        <div class="head-context"><span class="head-eyebrow">ACTIVE THREAD</span><strong>{{ chat.activeConversation?.title || '新的对话' }}</strong></div>
        <button class="model-chip" @click="router.push('/settings/models')"><ModelAvatar :model="modelLabel" size="small" variant="bare" /><span class="live-dot"></span>{{ modelLabel }} <i>↗</i></button>
      </header>

      <section ref="timeline" class="timeline">
        <div v-if="!chat.messages.length" class="welcome">
          <p class="serial">001 — AGENT WORKBENCH</p><h1>把想法<br /><em>变成行动。</em></h1>
          <p>一个连接模型、数据与工作流的执行型对话空间。</p>
          <div class="prompt-grid"><button @click="input = '帮我梳理一下这个项目的模块边界'">分析项目 <span>↗</span></button><button @click="input = '帮我起草一封简洁的项目进度邮件'">起草邮件 <span>↗</span></button><button @click="input = '给我一个下一步开发建议'">规划下一步 <span>↗</span></button></div>
        </div>
        <article v-for="message in chat.messages" :key="message.id" class="message" :class="message.role">
          <div class="avatar">
            <img v-if="message.role === 'user' && profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" />
            <span v-else-if="message.role === 'user'">{{ userInitials }}</span>
            <ModelAvatar v-else :model="modelLabel" />
          </div>
          <div class="message-body"><div class="message-meta"><strong>{{ message.role === 'user' ? userName : modelLabel }}</strong><time v-if="message.created_at" class="message-time">{{ formatMessageTime(message.created_at) }}</time><span class="message-status">{{ message.status === 'streaming' ? '正在推演' : '完成' }}</span></div>
            <template v-if="message.role === 'assistant' && message.timeline?.length">
              <template v-for="(event, index) in message.timeline" :key="index">
                <details v-if="event.type === 'reasoning_summary'" class="reasoning"><summary>推理摘要</summary><p>{{ event.content }}</p></details>
                <div v-else-if="event.type === 'tool_started' || event.type === 'tool_finished'" class="tool-event">{{ event.tool || '工具' }} · {{ event.content || (event.type === 'tool_started' ? '执行中' : '已完成') }}</div>
                <div v-else class="message-content markdown" v-html="renderMarkdown(event.content || '')"></div><b v-if="message.status === 'streaming' && index === message.timeline.length - 1" class="cursor"></b>
              </template>
            </template>
            <template v-else>
              <details v-if="message.reasoning_summary" class="reasoning"><summary>推理摘要</summary><p>{{ message.reasoning_summary }}</p></details>
              <div v-for="(event, index) in message.tool_events" :key="index" class="tool-event">{{ event.tool || '工具' }} · {{ event.content || '执行中' }}</div>
              <template v-if="message.role === 'user' && editingMessageId === message.id">
                <textarea v-model="editingMessageContent" class="message-edit" rows="3" @keydown.esc="cancelMessageEdit"></textarea>
                <div class="message-edit-actions"><button @click="cancelMessageEdit">取消</button><button class="primary" :disabled="!editingMessageContent.trim()" @click="saveMessageEdit(message)">保存并重试</button></div>
              </template>
              <div v-else class="message-content markdown" v-html="renderMarkdown(message.content)"></div><b v-if="message.status === 'streaming'" class="cursor"></b>
            </template>
            <div v-if="message.status !== 'streaming'" class="message-actions">
              <button v-if="message.role === 'user'" title="编辑后重新生成" @click="beginMessageEdit(message)">编辑</button>
              <button v-else title="重新生成此回答" @click="retryMessage(message)">重试</button>
              <button title="从这里创建新会话" @click="branchFrom(message)">创建分支</button>
              <span v-if="(message.sibling_count || 1) > 1" class="version-switch">
                <button :disabled="!message.sibling_index" title="上一个版本" @click="selectVersion(message, -1)">‹</button>
                <b>{{ (message.sibling_index || 0) + 1 }} / {{ message.sibling_count }}</b>
                <button :disabled="(message.sibling_index || 0) >= (message.sibling_count || 1) - 1" title="下一个版本" @click="selectVersion(message, 1)">›</button>
              </span>
            </div>
          </div>
        </article>
      </section>

      <aside v-if="conversationTurns.length" class="message-navigator" aria-label="对话轮次预览">
        <div class="navigator-track" :style="{ height: `${Math.min(560, Math.max(64, conversationTurns.length * 24))}px` }">
          <button
            v-for="(turn, index) in conversationTurns"
            :key="turn.user?.id || turn.assistant?.id || index"
            class="navigator-stop"
            :class="{ active: previewTurn === index, pending: turn.assistant?.status === 'streaming' }"
            :aria-label="`查看第 ${index + 1} 轮对话`"
            @mouseenter="previewTurn = index"
            @mouseleave="previewTurn = -1"
            @focus="previewTurn = index"
            @blur="previewTurn = -1"
          >
            <span class="navigator-mark"></span>
            <div v-if="previewTurn === index" class="turn-preview" role="tooltip">
              <div class="preview-question"><span>YOU</span><p>{{ previewText(turn.user) }}</p></div>
              <div class="preview-answer"><span>{{ modelLabel }}</span><p>{{ previewText(turn.assistant) }}</p></div>
            </div>
          </button>
        </div>
      </aside>

      <footer class="composer-wrap"><p v-if="chat.error" class="error-line">{{ chat.error }}</p><div class="composer"><textarea v-model="input" rows="1" placeholder="输入任务、问题或下一步…" @keydown="keydown"></textarea><div class="composer-actions"><span>Shift ↵ 换行</span><button v-if="chat.generating" class="stop" @click="chat.stop">■ 停止</button><button v-else class="send" :disabled="!input.trim()" @click="send">→</button></div></div><p class="disclaimer">OBSIDIAN 可以调用已连接的能力；请核对执行结果。</p></footer>
    </main>
    <div v-if="profileOpen" class="profile-backdrop" @click.self="profileOpen = false"><section class="profile-panel"><button class="close-panel" @click="profileOpen = false">×</button><p class="serial">PERSONAL NODE</p><div class="profile-hero"><img v-if="profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" /><span v-else>{{ userInitials }}</span></div><h2>{{ userName }}</h2><p>{{ profile?.email || userId }}</p><label class="avatar-upload"><input type="file" accept="image/png,image/jpeg,image/webp,image/gif" :disabled="profileBusy" @change="uploadAvatar" />{{ profileBusy ? '正在保存…' : '上传头像' }}</label><small>PNG、JPG、WebP 或 GIF，最大 1.4 MB</small><p v-if="profileError" class="profile-error">{{ profileError }}</p></section></div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&display=swap');
.workbench{--ink:#111;--paper:#ece9e2;--cream:#f7f5f0;--acid:#d9ff36;--line:rgba(17,17,17,.13);height:100dvh;overflow:hidden;background:var(--paper);color:var(--ink);display:grid;grid-template-columns:286px minmax(0,1fr);font-family:Manrope,sans-serif;position:relative}.workbench:before{content:'';position:fixed;inset:0;pointer-events:none;opacity:.4;background-image:linear-gradient(rgba(0,0,0,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,.025) 1px,transparent 1px);background-size:32px 32px}.rail{z-index:2;height:100dvh;min-height:0;overflow:hidden;background:#171717;color:#f1efe8;padding:28px 18px 20px;display:flex;flex-direction:column}.rail-brand{letter-spacing:.13em;font-size:13px;font-weight:800;display:flex;align-items:center;gap:9px;padding:0 10px 30px}.rail-brand i{font-style:normal;color:var(--acid)}.brand-orbit{height:17px;width:17px;border:2px solid var(--acid);border-radius:50%;position:relative}.brand-orbit:after{content:'';position:absolute;inset:3px;border-radius:50%;background:var(--acid)}.new-session{border:1px solid rgba(255,255,255,.27);background:transparent;color:#fff;padding:13px 12px;text-align:left;font:600 13px Manrope;cursor:pointer;transition:.25s;margin-bottom:30px}.new-session span{color:var(--acid);font-size:20px;line-height:0;vertical-align:-2px;margin-right:8px}.new-session kbd{float:right;color:#838383;font:10px 'DM Mono';padding-top:4px}.new-session:hover{background:var(--acid);color:#111;border-color:var(--acid)}.rail-label,.head-eyebrow,.serial{font:10px 'DM Mono';letter-spacing:.15em;text-transform:uppercase}.rail-label{color:#777;padding:0 10px 10px}.conversation-list{flex:1;min-height:0;overflow:auto}.conversation-row{display:flex;align-items:center;min-width:0}.conversation-main{min-width:0;flex:1;display:flex;align-items:center;gap:9px;border:0;background:transparent;color:#a9a9a9;padding:10px;text-align:left;font:500 12px Manrope;cursor:pointer;transition:.2s}.conversation-row:hover .conversation-main,.conversation-row.active .conversation-main{background:#2a2a2a;color:#fff}.conversation-signal{width:5px;height:5px;background:#555;border-radius:50%;flex:none}.active .conversation-signal{background:var(--acid);box-shadow:0 0 8px var(--acid)}.conversation-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}.conversation-actions{display:flex;opacity:0;transition:.2s}.conversation-row:hover .conversation-actions,.conversation-row.active .conversation-actions{opacity:1}.conversation-actions button{border:0;background:transparent;color:#929292;cursor:pointer;font-size:15px;padding:5px}.conversation-actions button:hover{color:var(--acid)}.rename-input{width:100%;min-width:0;border:0;outline:1px solid var(--acid);background:#333;color:#fff;padding:3px 5px;font:500 12px Manrope}.empty-list{color:#666;text-align:center;padding:35px 0;font:11px/1.8 'DM Mono'}.rail-footer{border-top:1px solid #333;padding-top:12px;display:grid;gap:4px}.rail-footer>button{background:transparent;border:0;color:#999;padding:8px;text-align:left;font:11px Manrope;cursor:pointer}.rail-footer>button:hover{color:var(--acid)}.user-card{display:grid;grid-template-columns:30px 1fr auto;align-items:center;gap:9px;margin-bottom:5px}.user-card img,.user-initials{width:30px;height:30px;border-radius:50%;object-fit:cover;background:var(--acid);color:#111;display:grid;place-items:center;font:9px 'DM Mono'}.user-card strong,.user-card small{display:block;max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.user-card strong{font-size:11px;color:#e9e8df}.user-card small{font:9px 'DM Mono';color:#777;margin-top:2px}.user-card b{font-size:16px;font-weight:400}.dialogue{z-index:1;min-width:0;height:100dvh;min-height:0;overflow:hidden;display:grid;grid-template-rows:82px minmax(0,1fr) auto}.dialogue-head{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding:0 42px;background:rgba(247,245,240,.55);backdrop-filter:blur(16px)}.head-context{display:grid;gap:2px}.head-eyebrow{color:#7b7a76}.head-context strong{font-size:14px;letter-spacing:-.02em}.model-chip{display:flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--cream);padding:5px 11px 5px 5px;border-radius:30px;font:11px 'DM Mono';cursor:pointer}.live-dot{width:6px;height:6px;border-radius:50%;background:#31b45f;box-shadow:0 0 0 3px rgba(49,180,95,.14)}.model-chip i{font-style:normal;margin-left:2px}.mobile-menu{display:none}.timeline{min-height:0;overflow:auto;padding:52px clamp(24px,8vw,130px) 28px;scroll-behavior:smooth}.welcome{max-width:735px;animation:rise .7s cubic-bezier(.22,1,.36,1) both}.serial{color:#777;margin-bottom:25px}.welcome h1{font:700 clamp(48px,7vw,98px)/.92 'Playfair Display';letter-spacing:-.07em;margin:0}.welcome h1 em{font-weight:600;color:#777}.welcome>p:not(.serial){max-width:400px;margin:27px 0 36px;color:#585752;line-height:1.7;font-size:14px}.prompt-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.prompt-grid button{background:rgba(255,255,255,.38);border:1px solid var(--line);padding:17px 14px;text-align:left;font:600 12px/1.4 Manrope;cursor:pointer;min-height:84px;transition:.25s}.prompt-grid button:hover{background:var(--acid);transform:translateY(-3px);box-shadow:4px 5px 0 #111}.prompt-grid span{display:block;margin-top:11px;font-size:15px}.message{display:grid;grid-template-columns:34px minmax(0,1fr);gap:16px;max-width:810px;margin:0 auto 35px;animation:rise .35s ease both}.avatar{height:31px;width:31px;border-radius:50%;display:grid;place-items:center;background:#171717;color:var(--acid);overflow:visible}.avatar>img{width:31px;height:31px;border-radius:50%;object-fit:cover}.avatar>span{font:9px 'DM Mono';background:var(--acid);color:#111;width:31px;height:31px;display:grid;place-items:center;border-radius:50%}.avatar :deep(.model-avatar){width:31px;height:31px;border-radius:50%;box-shadow:none;clip-path:none}.message-meta{font:10px 'DM Mono';letter-spacing:.1em;margin:5px 0 10px}.message-meta span{color:#888;margin-left:7px}.message-content{white-space:pre-wrap;margin:0;font-size:14px;line-height:1.85;letter-spacing:-.01em}.message.user .message-content{font-weight:600}.reasoning,.tool-event{margin:0 0 10px;border-left:2px solid #a0a099;padding:8px 11px;background:rgba(0,0,0,.035);font:11px/1.6 'DM Mono';color:#666}.reasoning summary{cursor:pointer;color:#333}.reasoning p{margin:6px 0 0}.tool-event{border-left-color:var(--acid);color:#4b4b43}.cursor{display:inline-block;width:7px;height:16px;background:#111;margin-left:4px;vertical-align:-3px;animation:blink .8s step-end infinite}.composer-wrap{padding:0 clamp(24px,8vw,130px) 22px;background:linear-gradient(transparent,var(--paper) 18%)}.composer{border:1px solid #1b1b1b;background:#fdfcf9;padding:15px 16px 10px;box-shadow:6px 6px 0 #1b1b1b;transition:.25s}.composer:focus-within{box-shadow:9px 9px 0 var(--acid);transform:translate(-2px,-2px)}textarea{display:block;width:100%;resize:none;border:0;outline:0;background:transparent;font:500 14px/1.6 Manrope;min-height:28px;max-height:160px}.composer-actions{display:flex;align-items:center;justify-content:space-between;margin-top:9px;color:#8b8983;font:9px 'DM Mono'}.send,.stop{border:0;cursor:pointer;font:700 15px Manrope;padding:5px 11px;background:var(--acid);color:#111}.send:disabled{opacity:.3;cursor:not-allowed}.stop{font-size:10px;background:#1b1b1b;color:#fff}.disclaimer{font:9px 'DM Mono';color:#898783;text-align:center;margin:14px 0 0}.error-line,.profile-error{color:#b24038;font:11px 'DM Mono';margin:0 0 8px}.profile-backdrop{position:fixed;z-index:20;inset:0;background:rgba(0,0,0,.55);display:grid;place-items:center;padding:20px;backdrop-filter:blur(8px)}.profile-panel{position:relative;width:min(100%,380px);padding:36px;background:#f8f6ef;box-shadow:12px 12px 0 #111;text-align:center}.close-panel{position:absolute;right:12px;top:8px;background:transparent;border:0;font-size:25px;cursor:pointer}.profile-hero{width:94px;height:94px;margin:0 auto 18px;border:3px solid #111;box-shadow:5px 5px 0 var(--acid);overflow:hidden;background:#171717;color:var(--acid);display:grid;place-items:center;font:28px 'DM Mono'}.profile-hero img{width:100%;height:100%;object-fit:cover}.profile-panel h2{margin:0;font:700 31px 'Playfair Display'}.profile-panel>p:not(.serial):not(.profile-error){margin:6px 0 25px;color:#777;font-size:12px}.avatar-upload{display:inline-block;background:var(--acid);border:1px solid #111;padding:10px 16px;font:700 12px Manrope;cursor:pointer}.avatar-upload input{display:none}.profile-panel small{display:block;margin-top:11px;color:#777;font:9px 'DM Mono'}.profile-error{margin:14px 0 0}.markdown :deep(p){margin:0 0 12px}.markdown :deep(p:last-child){margin-bottom:0}.markdown :deep(h1),.markdown :deep(h2),.markdown :deep(h3),.markdown :deep(h4){margin:22px 0 10px;line-height:1.2;letter-spacing:-.03em}.markdown :deep(h1){font-size:1.55em}.markdown :deep(h2){font-size:1.3em}.markdown :deep(h3){font-size:1.12em}.markdown :deep(ul),.markdown :deep(ol){margin:8px 0 13px;padding-left:24px}.markdown :deep(li+li){margin-top:4px}.markdown :deep(blockquote){margin:12px 0;padding:7px 13px;border-left:3px solid var(--acid);background:rgba(0,0,0,.045);color:#575650}.markdown :deep(pre){margin:14px 0;padding:14px;overflow:auto;background:#171717;color:#f6f5ee;border-radius:2px;font:12px/1.65 'DM Mono',monospace}.markdown :deep(pre code){padding:0;background:transparent;color:inherit}.markdown :deep(code){padding:2px 5px;background:rgba(17,17,17,.1);font:12px 'DM Mono',monospace}.markdown :deep(a){color:#456d00;text-decoration:underline;text-decoration-color:var(--acid);text-underline-offset:3px}.markdown :deep(table){width:100%;border-collapse:collapse;margin:13px 0;font-size:12px}.markdown :deep(th),.markdown :deep(td){padding:7px 9px;border:1px solid var(--line);text-align:left}.markdown :deep(th){background:rgba(0,0,0,.055)}@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}@keyframes blink{50%{opacity:0}}@media(max-width:760px){.workbench{grid-template-columns:1fr}.rail{position:fixed;inset:0 auto 0 0;width:280px;transform:translateX(-102%);transition:.3s;box-shadow:20px 0 50px rgba(0,0,0,.2)}.sidebar-open .rail{transform:none}.dialogue-head{padding:0 20px}.mobile-menu{display:block;border:0;background:transparent;font-size:19px}.timeline{padding:35px 20px 20px}.composer-wrap{padding:0 22px 20px}.prompt-grid{grid-template-columns:1fr}.welcome h1{font-size:58px}.model-chip{max-width:180px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.dialogue{position:relative}.message-navigator{position:absolute;z-index:4;left:13px;top:50%;width:30px;transform:translateY(-50%);pointer-events:none}.navigator-track{display:flex;flex-direction:column;align-items:center;gap:2px;padding:5px 0}.navigator-stop{position:relative;display:grid;place-items:center;flex:1 1 0;min-height:4px;width:100%;border:0;background:transparent;padding:0;cursor:default;pointer-events:auto}.navigator-mark{height:2px;width:9px;background:#b8b6b0;transition:width .18s ease,background .18s ease,transform .18s ease}.navigator-stop:hover .navigator-mark,.navigator-stop:focus-visible .navigator-mark,.navigator-stop.active .navigator-mark{width:21px;background:#191919;transform:translateX(5px)}.navigator-stop.pending .navigator-mark{background:#6d6c66;animation:marker-pulse .85s ease-in-out infinite}.navigator-stop:focus-visible{outline:0}.turn-preview{position:absolute;z-index:5;left:32px;top:50%;width:min(390px,calc(100vw - 390px));max-height:210px;overflow:hidden;transform:translateY(-50%);border:1px solid rgba(17,17,17,.13);border-radius:20px;background:rgba(253,252,249,.97);box-shadow:0 15px 34px rgba(17,17,17,.13),0 2px 8px rgba(17,17,17,.06);padding:16px 17px;text-align:left;backdrop-filter:blur(14px);cursor:default;animation:preview-in .18s cubic-bezier(.22,1,.36,1) both}.turn-preview:before{content:'';position:absolute;left:-5px;top:50%;width:9px;height:9px;background:#fdfcf9;border-left:1px solid rgba(17,17,17,.13);border-bottom:1px solid rgba(17,17,17,.13);transform:translateY(-50%) rotate(45deg)}.preview-question,.preview-answer{position:relative}.preview-question{padding-bottom:11px;border-bottom:1px solid rgba(17,17,17,.09)}.preview-answer{padding-top:11px}.preview-question span,.preview-answer span{display:block;margin-bottom:4px;color:#8c8a84;font:9px 'DM Mono';letter-spacing:.12em;text-transform:uppercase}.preview-answer span{color:#5a7117}.preview-question p,.preview-answer p{display:-webkit-box;overflow:hidden;margin:0;color:#242321;font:600 13px/1.45 Manrope;-webkit-box-orient:vertical;-webkit-line-clamp:2}.preview-answer p{font-weight:500;color:#77756f}@keyframes marker-pulse{50%{opacity:.35;transform:scaleX(.65)}}@keyframes preview-in{from{opacity:0;transform:translate(-5px,-50%)}to{opacity:1;transform:translateY(-50%)}}@media(max-width:900px){.message-navigator{display:none}}
.conversation-copy{min-width:0;flex:1;display:grid;gap:3px}.conversation-date{color:#777;font:9px 'DM Mono';letter-spacing:.03em}.conversation-row.active .conversation-date{color:#9e9e9a}.message-meta{display:flex;align-items:center;gap:8px}.message-meta strong{font:inherit;font-weight:500}.message-time{color:#8d8b85;font:9px 'DM Mono';letter-spacing:.04em}.message-status{margin-left:0!important}.message-status:before{content:'·';margin-right:8px;color:#aaa8a2}
.message-actions{display:flex;align-items:center;gap:5px;margin-top:13px;opacity:0;transition:opacity .18s}.message:hover .message-actions{opacity:1}.message-actions button,.message-edit-actions button{border:1px solid transparent;background:transparent;color:#777;padding:3px 6px;font:10px 'DM Mono';cursor:pointer}.message-actions button:hover,.message-edit-actions button:hover{border-color:var(--line);background:#fff;color:#111}.message-actions button:disabled{cursor:not-allowed;opacity:.3}.version-switch{display:flex;align-items:center;gap:3px;margin-left:3px;padding-left:5px;border-left:1px solid var(--line)}.version-switch b{min-width:31px;text-align:center;color:#555;font:9px 'DM Mono'}.message-edit{width:100%;margin:0;border:1px solid #191919;outline:0;background:#fffdf7;padding:9px 10px;font:500 13px/1.65 Manrope;resize:vertical}.message-edit:focus{box-shadow:3px 3px 0 var(--acid)}.message-edit-actions{display:flex;justify-content:flex-end;gap:6px;margin-top:7px}.message-edit-actions .primary{border-color:#171717;background:var(--acid);color:#111}.message.user .message-actions{justify-content:flex-end}
</style>
