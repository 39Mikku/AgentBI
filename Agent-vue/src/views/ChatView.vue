<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ModelAvatar from '@/components/ModelAvatar.vue'
import { getUserProfile, saveUserAvatar } from '@/api/user-profile'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { renderMarkdown } from '@/utils/markdown'
import { createRuntimeContext } from '@/utils/runtime-context'

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
const timeline = ref<HTMLElement | null>(null)
const userId = computed(() => auth.email || 'local-user')
const modelLabel = computed(() => chat.preferences.model || '选择模型')
const userName = computed(() => profile.value?.username || (userId.value.includes('@') ? userId.value.split('@')[0] || userId.value : userId.value))
const userInitials = computed(() => userName.value.slice(0, 2).toUpperCase())

function send() { const value = input.value.trim(); if (value) { input.value = ''; void chat.send(userId.value, value, createRuntimeContext(userName.value, navigator.language, Intl.DateTimeFormat().resolvedOptions().timeZone)) } }
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
            <span v-else class="conversation-title">{{ item.title }}</span>
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
          <div class="message-body"><div class="message-meta">{{ message.role === 'user' ? userName : modelLabel }} <span>{{ message.status === 'streaming' ? '正在推演' : '完成' }}</span></div>
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
              <div class="message-content markdown" v-html="renderMarkdown(message.content)"></div><b v-if="message.status === 'streaming'" class="cursor"></b>
            </template>
          </div>
        </article>
      </section>

      <footer class="composer-wrap"><p v-if="chat.error" class="error-line">{{ chat.error }}</p><div class="composer"><textarea v-model="input" rows="1" placeholder="输入任务、问题或下一步…" @keydown="keydown"></textarea><div class="composer-actions"><span>Shift ↵ 换行</span><button v-if="chat.generating" class="stop" @click="chat.stop">■ 停止</button><button v-else class="send" :disabled="!input.trim()" @click="send">→</button></div></div><p class="disclaimer">OBSIDIAN 可以调用已连接的能力；请核对执行结果。</p></footer>
    </main>
    <div v-if="profileOpen" class="profile-backdrop" @click.self="profileOpen = false"><section class="profile-panel"><button class="close-panel" @click="profileOpen = false">×</button><p class="serial">PERSONAL NODE</p><div class="profile-hero"><img v-if="profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" /><span v-else>{{ userInitials }}</span></div><h2>{{ userName }}</h2><p>{{ profile?.email || userId }}</p><label class="avatar-upload"><input type="file" accept="image/png,image/jpeg,image/webp,image/gif" :disabled="profileBusy" @change="uploadAvatar" />{{ profileBusy ? '正在保存…' : '上传头像' }}</label><small>PNG、JPG、WebP 或 GIF，最大 1.4 MB</small><p v-if="profileError" class="profile-error">{{ profileError }}</p></section></div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&display=swap');
.workbench{--ink:#111;--paper:#ece9e2;--cream:#f7f5f0;--acid:#d9ff36;--line:rgba(17,17,17,.13);height:100dvh;overflow:hidden;background:var(--paper);color:var(--ink);display:grid;grid-template-columns:286px minmax(0,1fr);font-family:Manrope,sans-serif;position:relative}.workbench:before{content:'';position:fixed;inset:0;pointer-events:none;opacity:.4;background-image:linear-gradient(rgba(0,0,0,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,0,0,.025) 1px,transparent 1px);background-size:32px 32px}.rail{z-index:2;height:100dvh;min-height:0;overflow:hidden;background:#171717;color:#f1efe8;padding:28px 18px 20px;display:flex;flex-direction:column}.rail-brand{letter-spacing:.13em;font-size:13px;font-weight:800;display:flex;align-items:center;gap:9px;padding:0 10px 30px}.rail-brand i{font-style:normal;color:var(--acid)}.brand-orbit{height:17px;width:17px;border:2px solid var(--acid);border-radius:50%;position:relative}.brand-orbit:after{content:'';position:absolute;inset:3px;border-radius:50%;background:var(--acid)}.new-session{border:1px solid rgba(255,255,255,.27);background:transparent;color:#fff;padding:13px 12px;text-align:left;font:600 13px Manrope;cursor:pointer;transition:.25s;margin-bottom:30px}.new-session span{color:var(--acid);font-size:20px;line-height:0;vertical-align:-2px;margin-right:8px}.new-session kbd{float:right;color:#838383;font:10px 'DM Mono';padding-top:4px}.new-session:hover{background:var(--acid);color:#111;border-color:var(--acid)}.rail-label,.head-eyebrow,.serial{font:10px 'DM Mono';letter-spacing:.15em;text-transform:uppercase}.rail-label{color:#777;padding:0 10px 10px}.conversation-list{flex:1;min-height:0;overflow:auto}.conversation-row{display:flex;align-items:center;min-width:0}.conversation-main{min-width:0;flex:1;display:flex;align-items:center;gap:9px;border:0;background:transparent;color:#a9a9a9;padding:10px;text-align:left;font:500 12px Manrope;cursor:pointer;transition:.2s}.conversation-row:hover .conversation-main,.conversation-row.active .conversation-main{background:#2a2a2a;color:#fff}.conversation-signal{width:5px;height:5px;background:#555;border-radius:50%;flex:none}.active .conversation-signal{background:var(--acid);box-shadow:0 0 8px var(--acid)}.conversation-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}.conversation-actions{display:flex;opacity:0;transition:.2s}.conversation-row:hover .conversation-actions,.conversation-row.active .conversation-actions{opacity:1}.conversation-actions button{border:0;background:transparent;color:#929292;cursor:pointer;font-size:15px;padding:5px}.conversation-actions button:hover{color:var(--acid)}.rename-input{width:100%;min-width:0;border:0;outline:1px solid var(--acid);background:#333;color:#fff;padding:3px 5px;font:500 12px Manrope}.empty-list{color:#666;text-align:center;padding:35px 0;font:11px/1.8 'DM Mono'}.rail-footer{border-top:1px solid #333;padding-top:12px;display:grid;gap:4px}.rail-footer>button{background:transparent;border:0;color:#999;padding:8px;text-align:left;font:11px Manrope;cursor:pointer}.rail-footer>button:hover{color:var(--acid)}.user-card{display:grid;grid-template-columns:30px 1fr auto;align-items:center;gap:9px;margin-bottom:5px}.user-card img,.user-initials{width:30px;height:30px;border-radius:50%;object-fit:cover;background:var(--acid);color:#111;display:grid;place-items:center;font:9px 'DM Mono'}.user-card strong,.user-card small{display:block;max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.user-card strong{font-size:11px;color:#e9e8df}.user-card small{font:9px 'DM Mono';color:#777;margin-top:2px}.user-card b{font-size:16px;font-weight:400}.dialogue{z-index:1;min-width:0;height:100dvh;min-height:0;overflow:hidden;display:grid;grid-template-rows:82px minmax(0,1fr) auto}.dialogue-head{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding:0 42px;background:rgba(247,245,240,.55);backdrop-filter:blur(16px)}.head-context{display:grid;gap:2px}.head-eyebrow{color:#7b7a76}.head-context strong{font-size:14px;letter-spacing:-.02em}.model-chip{display:flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--cream);padding:5px 11px 5px 5px;border-radius:30px;font:11px 'DM Mono';cursor:pointer}.live-dot{width:6px;height:6px;border-radius:50%;background:#31b45f;box-shadow:0 0 0 3px rgba(49,180,95,.14)}.model-chip i{font-style:normal;margin-left:2px}.mobile-menu{display:none}.timeline{min-height:0;overflow:auto;padding:52px clamp(24px,8vw,130px) 28px;scroll-behavior:smooth}.welcome{max-width:735px;animation:rise .7s cubic-bezier(.22,1,.36,1) both}.serial{color:#777;margin-bottom:25px}.welcome h1{font:700 clamp(48px,7vw,98px)/.92 'Playfair Display';letter-spacing:-.07em;margin:0}.welcome h1 em{font-weight:600;color:#777}.welcome>p:not(.serial){max-width:400px;margin:27px 0 36px;color:#585752;line-height:1.7;font-size:14px}.prompt-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.prompt-grid button{background:rgba(255,255,255,.38);border:1px solid var(--line);padding:17px 14px;text-align:left;font:600 12px/1.4 Manrope;cursor:pointer;min-height:84px;transition:.25s}.prompt-grid button:hover{background:var(--acid);transform:translateY(-3px);box-shadow:4px 5px 0 #111}.prompt-grid span{display:block;margin-top:11px;font-size:15px}.message{display:grid;grid-template-columns:34px minmax(0,1fr);gap:16px;max-width:810px;margin:0 auto 35px;animation:rise .35s ease both}.avatar{height:31px;width:31px;border-radius:50%;display:grid;place-items:center;background:#171717;color:var(--acid);overflow:visible}.avatar>img{width:31px;height:31px;border-radius:50%;object-fit:cover}.avatar>span{font:9px 'DM Mono';background:var(--acid);color:#111;width:31px;height:31px;display:grid;place-items:center;border-radius:50%}.avatar :deep(.model-avatar){width:31px;height:31px;border-radius:50%;box-shadow:none;clip-path:none}.message-meta{font:10px 'DM Mono';letter-spacing:.1em;margin:5px 0 10px}.message-meta span{color:#888;margin-left:7px}.message-content{white-space:pre-wrap;margin:0;font-size:14px;line-height:1.85;letter-spacing:-.01em}.message.user .message-content{font-weight:600}.reasoning,.tool-event{margin:0 0 10px;border-left:2px solid #a0a099;padding:8px 11px;background:rgba(0,0,0,.035);font:11px/1.6 'DM Mono';color:#666}.reasoning summary{cursor:pointer;color:#333}.reasoning p{margin:6px 0 0}.tool-event{border-left-color:var(--acid);color:#4b4b43}.cursor{display:inline-block;width:7px;height:16px;background:#111;margin-left:4px;vertical-align:-3px;animation:blink .8s step-end infinite}.composer-wrap{padding:0 clamp(24px,8vw,130px) 22px;background:linear-gradient(transparent,var(--paper) 18%)}.composer{border:1px solid #1b1b1b;background:#fdfcf9;padding:15px 16px 10px;box-shadow:6px 6px 0 #1b1b1b;transition:.25s}.composer:focus-within{box-shadow:9px 9px 0 var(--acid);transform:translate(-2px,-2px)}textarea{display:block;width:100%;resize:none;border:0;outline:0;background:transparent;font:500 14px/1.6 Manrope;min-height:28px;max-height:160px}.composer-actions{display:flex;align-items:center;justify-content:space-between;margin-top:9px;color:#8b8983;font:9px 'DM Mono'}.send,.stop{border:0;cursor:pointer;font:700 15px Manrope;padding:5px 11px;background:var(--acid);color:#111}.send:disabled{opacity:.3;cursor:not-allowed}.stop{font-size:10px;background:#1b1b1b;color:#fff}.disclaimer{font:9px 'DM Mono';color:#898783;text-align:center;margin:14px 0 0}.error-line,.profile-error{color:#b24038;font:11px 'DM Mono';margin:0 0 8px}.profile-backdrop{position:fixed;z-index:20;inset:0;background:rgba(0,0,0,.55);display:grid;place-items:center;padding:20px;backdrop-filter:blur(8px)}.profile-panel{position:relative;width:min(100%,380px);padding:36px;background:#f8f6ef;box-shadow:12px 12px 0 #111;text-align:center}.close-panel{position:absolute;right:12px;top:8px;background:transparent;border:0;font-size:25px;cursor:pointer}.profile-hero{width:94px;height:94px;margin:0 auto 18px;border:3px solid #111;box-shadow:5px 5px 0 var(--acid);overflow:hidden;background:#171717;color:var(--acid);display:grid;place-items:center;font:28px 'DM Mono'}.profile-hero img{width:100%;height:100%;object-fit:cover}.profile-panel h2{margin:0;font:700 31px 'Playfair Display'}.profile-panel>p:not(.serial):not(.profile-error){margin:6px 0 25px;color:#777;font-size:12px}.avatar-upload{display:inline-block;background:var(--acid);border:1px solid #111;padding:10px 16px;font:700 12px Manrope;cursor:pointer}.avatar-upload input{display:none}.profile-panel small{display:block;margin-top:11px;color:#777;font:9px 'DM Mono'}.profile-error{margin:14px 0 0}.markdown :deep(p){margin:0 0 12px}.markdown :deep(p:last-child){margin-bottom:0}.markdown :deep(h1),.markdown :deep(h2),.markdown :deep(h3),.markdown :deep(h4){margin:22px 0 10px;line-height:1.2;letter-spacing:-.03em}.markdown :deep(h1){font-size:1.55em}.markdown :deep(h2){font-size:1.3em}.markdown :deep(h3){font-size:1.12em}.markdown :deep(ul),.markdown :deep(ol){margin:8px 0 13px;padding-left:24px}.markdown :deep(li+li){margin-top:4px}.markdown :deep(blockquote){margin:12px 0;padding:7px 13px;border-left:3px solid var(--acid);background:rgba(0,0,0,.045);color:#575650}.markdown :deep(pre){margin:14px 0;padding:14px;overflow:auto;background:#171717;color:#f6f5ee;border-radius:2px;font:12px/1.65 'DM Mono',monospace}.markdown :deep(pre code){padding:0;background:transparent;color:inherit}.markdown :deep(code){padding:2px 5px;background:rgba(17,17,17,.1);font:12px 'DM Mono',monospace}.markdown :deep(a){color:#456d00;text-decoration:underline;text-decoration-color:var(--acid);text-underline-offset:3px}.markdown :deep(table){width:100%;border-collapse:collapse;margin:13px 0;font-size:12px}.markdown :deep(th),.markdown :deep(td){padding:7px 9px;border:1px solid var(--line);text-align:left}.markdown :deep(th){background:rgba(0,0,0,.055)}@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}@keyframes blink{50%{opacity:0}}@media(max-width:760px){.workbench{grid-template-columns:1fr}.rail{position:fixed;inset:0 auto 0 0;width:280px;transform:translateX(-102%);transition:.3s;box-shadow:20px 0 50px rgba(0,0,0,.2)}.sidebar-open .rail{transform:none}.dialogue-head{padding:0 20px}.mobile-menu{display:block;border:0;background:transparent;font-size:19px}.timeline{padding:35px 20px 20px}.composer-wrap{padding:0 22px 20px}.prompt-grid{grid-template-columns:1fr}.welcome h1{font-size:58px}.model-chip{max-width:180px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
</style>
