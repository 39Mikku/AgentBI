<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ModelAvatar from '@/components/ModelAvatar.vue'
import TimelineCard from '@/components/cards/TimelineCard.vue'
import BilibiliPlayerModal from '@/components/BilibiliPlayerModal.vue'
import AppModeSwitcher from '@/components/AppModeSwitcher.vue'
import ToolEventDetails from '@/components/chat/ToolEventDetails.vue'
import AttachmentComposer from '@/components/chat/AttachmentComposer.vue'
import MessageAssets from '@/components/chat/MessageAssets.vue'
import ImageSourcePicker from '@/components/ImageSourcePicker.vue'
import { getUserProfile, saveUserAvatar } from '@/api/user-profile'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { usePlayerStore } from '@/stores/player'
import { renderMarkdown } from '@/utils/markdown'
import { shouldRefreshUserProfile } from '@/utils/profile-refresh'
import { createRuntimeContext } from '@/utils/runtime-context'
import { copyMarkdown } from '@/utils/clipboard'
import { isGeminiThinkingModel, renderReasoningMarkdown } from '@/utils/gemini-thinking'
import { normalizeReasoningLevel, reasoningChoices } from '@/utils/model-reasoning'
import type { ChatMessage, StudioAsset } from '@/api/chat-types'
import type { BilibiliVideo } from '@/utils/bilibili-player'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const chat = useChatStore()
const player = usePlayerStore()
const input = ref('')
const pendingAssets = ref<StudioAsset[]>([])
const attachmentBusy = ref(false)
const copiedMessageId = ref('')
const menuOpen = ref(false)
const assistantMenuOpen = ref(false)
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
const activeBilibiliVideo = ref<BilibiliVideo | null>(null)
const userId = computed(() => auth.email || 'local-user')
const modelLabel = computed(() => chat.preferences.model || '选择模型')
const thinkingLevels = computed(() => reasoningChoices(chat.preferences.model))
const showThinkingControl = computed(() => thinkingLevels.value.length > 0)
const userName = computed(
  () =>
    profile.value?.username ||
    (userId.value.includes('@') ? userId.value.split('@')[0] || userId.value : userId.value),
)
const userInitials = computed(() => userName.value.slice(0, 2).toUpperCase())
const assistantName = computed(() => chat.activeAssistant?.name || '默认助手')
const assistantInitials = computed(() => assistantName.value.slice(0, 2).toUpperCase())

watch(
  () => chat.preferences.model,
  (model) => {
    chat.preferences.thinkingLevel = normalizeReasoningLevel(
      model,
      chat.preferences.thinkingLevel,
    )
  },
  { immediate: true },
)
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

function renderTimelineMarkdown(message: ChatMessage, source: string) {
  const cardImageUrls = (message.timeline || [])
    .filter((event) => event.type === 'card' && event.kind === 'image.generated')
    .map((event) => event.payload?.url)
    .filter((url): url is string => typeof url === 'string')
  return renderMarkdown(source, cardImageUrls)
}

function timelineCardPayload(message: ChatMessage, payload?: Record<string, unknown>) {
  const result = { ...(payload || {}) }
  const assetId = typeof result.asset_id === 'string' ? result.asset_id : ''
  const asset = message.assets?.find((item) => item.id === assetId)
  if (asset?.status === 'deleted' || asset?.deleted_at) {
    result.deleted = true
    result.url = ''
  }
  return result
}

function parseTimestamp(value?: string) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function isSameDay(left: Date, right: Date) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  )
}

function formatClock(date: Date) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

function formatMessageTime(value?: string) {
  const date = parseTimestamp(value)
  if (!date) return ''
  const now = new Date()
  if (isSameDay(date, now)) return formatClock(date)
  const datePart = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(
    date,
  )
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
  if (date.getFullYear() === now.getFullYear())
    return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  }).format(date)
}

function send() {
  const value = input.value.trim()
  if ((value || pendingAssets.value.length) && !attachmentBusy.value) {
    const assets = [...pendingAssets.value]
    input.value = ''
    pendingAssets.value = []
    void chat.send(
      userId.value,
      value,
      createRuntimeContext(
        userName.value,
        navigator.language,
        Intl.DateTimeFormat().resolvedOptions().timeZone,
      ),
      assets,
    )
  }
}
function runtimeContext() {
  return createRuntimeContext(
    userName.value,
    navigator.language,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  )
}
function retryMessage(message: ChatMessage) {
  void chat.retry(userId.value, message.id, runtimeContext())
}
function beginMessageEdit(message: ChatMessage) {
  editingMessageId.value = message.id
  editingMessageContent.value = message.content
}
function cancelMessageEdit() {
  editingMessageId.value = ''
  editingMessageContent.value = ''
}
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
function branchFrom(message: ChatMessage) {
  void chat.branch(userId.value, message.id)
}
async function copyReply(message: ChatMessage) {
  try {
    await copyMarkdown(message.content)
    copiedMessageId.value = message.id
    window.setTimeout(() => {
      if (copiedMessageId.value === message.id) copiedMessageId.value = ''
    }, 1600)
  } catch (reason) {
    chat.error = reason instanceof Error ? reason.message : '复制失败'
  }
}
function openBilibiliVideo(video: BilibiliVideo) {
  activeBilibiliVideo.value = video
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}
async function newChat() {
  await chat.create(userId.value)
  menuOpen.value = false
}
function switchAssistant(id: string) {
  assistantMenuOpen.value = false
  void chat.selectAssistant(id, userId.value)
}
function logout() {
  auth.logout()
  void router.push('/')
}
function beginRename(id: string, title: string) {
  editingId.value = id
  editingTitle.value = title
}
function cancelRename() {
  editingId.value = ''
  editingTitle.value = ''
}
async function commitRename(id: string) {
  if (!editingTitle.value.trim()) return cancelRename()
  await chat.rename(id, userId.value, editingTitle.value)
  cancelRename()
}
async function loadProfile() {
  if (!shouldRefreshUserProfile(profile.value, userId.value)) return
  try {
    auth.setProfile(await getUserProfile(userId.value))
  } catch (error) {
    profileError.value = error instanceof Error ? error.message : '无法读取用户资料'
  }
}
async function saveProfileAvatar(dataUrl: string | null) {
  if (!dataUrl) return
  profileBusy.value = true
  profileError.value = ''
  try {
    auth.setProfile(await saveUserAvatar(userId.value, dataUrl))
  } catch (error) {
    profileError.value = error instanceof Error ? error.message : '头像保存失败'
  } finally {
    profileBusy.value = false
  }
}

watch(
  () => chat.messages.length,
  async () => {
    await nextTick()
    timeline.value?.scrollTo({ top: timeline.value.scrollHeight, behavior: 'smooth' })
  },
)
onMounted(async () => {
  await Promise.all([chat.load(userId.value), loadProfile()])
  const requestedConversation = typeof route.query.conversation === 'string' ? route.query.conversation : ''
  if (requestedConversation && requestedConversation !== chat.activeId)
    await chat.select(requestedConversation, userId.value)
})
</script>

<template>
  <div class="workbench" :class="{ 'sidebar-open': menuOpen }">
    <aside class="rail">
      <button class="rail-brand" type="button" title="返回主页" @click="router.push('/home')"><span class="brand-orbit"></span><span>OBSIDIAN</span><i>AI</i></button>
      <AppModeSwitcher active="studio" class="rail-mode-switcher" />
      <button class="new-session" @click="newChat"><span>＋</span> 新建对话 <kbd>⌘ K</kbd></button>
      <div class="assistant-switch">
        <button class="assistant-current" @click="assistantMenuOpen = !assistantMenuOpen">
          <img
            v-if="chat.activeAssistant?.avatar_data_url"
            :src="chat.activeAssistant.avatar_data_url"
            alt=""
          />
          <span v-else>{{ assistantInitials }}</span>
          <small>当前助手</small><strong>{{ assistantName }}</strong
          ><b>⌄</b>
        </button>
        <div v-if="assistantMenuOpen" class="assistant-menu">
          <button
            v-for="assistant in chat.assistants"
            :key="assistant.id"
            :class="{ active: assistant.id === chat.activeAssistantId }"
            @click="switchAssistant(assistant.id)"
          >
            <img v-if="assistant.avatar_data_url" :src="assistant.avatar_data_url" alt="" /><span
              v-else
              >{{ assistant.name.slice(0, 2).toUpperCase() }}</span
            >{{ assistant.name }}
          </button>
          <button class="assistant-manage" @click="router.push('/assistants')">管理助手 →</button>
        </div>
      </div>
      <div class="rail-label">会话档案</div>
      <nav class="conversation-list">
        <article
          v-for="item in chat.conversations"
          :key="item.id"
          class="conversation-row"
          :class="{ active: item.id === chat.activeId, generating: chat.isConversationGenerating(item.id) }"
        >
          <button class="conversation-main" @click="chat.select(item.id, userId)">
            <span class="conversation-signal"></span>
            <input
              v-if="editingId === item.id"
              v-model="editingTitle"
              class="rename-input"
              maxlength="120"
              autofocus
              @click.stop
              @keydown.enter.prevent="commitRename(item.id)"
              @keydown.esc.prevent="cancelRename"
              @blur="commitRename(item.id)"
            />
            <span v-else class="conversation-copy"
              ><span class="conversation-title">{{ item.title }}</span
              ><span v-if="chat.isConversationGenerating(item.id)" class="conversation-date generating-label">正在生成内容</span
              ><time
                v-else-if="item.last_message_at || item.updated_at || item.created_at"
                class="conversation-date"
                >{{
                  formatConversationDate(item.last_message_at || item.updated_at || item.created_at)
                }}</time
              ></span
            >
          </button>
          <span class="conversation-actions">
            <button title="重命名" @click.stop="beginRename(item.id, item.title)">✎</button>
            <button title="删除" @click.stop="chat.remove(item.id, userId)">×</button>
          </span>
        </article>
        <p v-if="!chat.conversations.length && !chat.loading" class="empty-list">
          没有历史会话<br />从右侧开始一段思考。
        </p>
      </nav>
      <div class="rail-footer">
        <button class="user-card" @click="profileOpen = true">
          <img v-if="profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" />
          <span v-else class="user-initials">{{ userInitials }}</span>
          <span
            ><strong>{{ userName }}</strong
            ><small>{{ profile?.email || userId }}</small></span
          ><b>›</b>
        </button>
        <button @click="router.push('/settings/models')">◈ 模型工作室</button>
        <button @click="router.push('/attachments')">▧ 附件库</button>
        <button @click="router.push('/toolbox')">⌘ 工具箱</button>
        <button @click="logout">↗ 退出会话</button>
      </div>
    </aside>

    <div v-if="chat.isSyncing" class="sync-indicator" role="status" aria-live="polite">
      <i></i><span>{{ chat.syncMessage }}</span>
    </div>
    <main class="dialogue">
      <header class="dialogue-head">
        <button class="mobile-menu" @click="menuOpen = !menuOpen">☰</button>
        <div class="head-context">
          <span class="head-eyebrow">ACTIVE THREAD</span
          ><strong>{{ chat.activeConversation?.title || '新的对话' }}</strong>
        </div>
        <button class="model-chip" @click="router.push('/settings/models')">
          <ModelAvatar :model="modelLabel" size="small" variant="bare" /><span
            class="live-dot"
          ></span
          >{{ modelLabel }} <i>↗</i>
        </button>
      </header>

      <section ref="timeline" class="timeline">
        <div v-if="!chat.messages.length" class="welcome">
          <p class="serial">001 — AGENT WORKBENCH</p>
          <h1>把想法<br /><em>变成行动。</em></h1>
          <p>一个连接模型、数据与工作流的执行型对话空间。</p>
          <div class="prompt-grid">
            <button @click="input = '帮我梳理一下这个项目的模块边界'">
              分析项目 <span>↗</span></button
            ><button @click="input = '帮我起草一封简洁的项目进度邮件'">
              起草邮件 <span>↗</span></button
            ><button @click="input = '给我一个下一步开发建议'">规划下一步 <span>↗</span></button>
          </div>
        </div>
        <article
          v-for="message in chat.messages"
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <div class="avatar">
            <img
              v-if="message.role === 'user' && profile?.avatar_data_url"
              :src="profile.avatar_data_url"
              alt=""
            />
            <span v-else-if="message.role === 'user'">{{ userInitials }}</span>
            <img
              v-else-if="chat.activeAssistant?.avatar_data_url"
              :src="chat.activeAssistant.avatar_data_url"
              alt=""
            />
            <ModelAvatar v-else :model="modelLabel" />
          </div>
          <div class="message-body">
            <div class="message-meta">
              <strong>{{ message.role === 'user' ? userName : assistantName }}</strong
              ><time v-if="message.created_at" class="message-time">{{
                formatMessageTime(message.created_at)
              }}</time
              ><span class="message-status">{{
                message.status === 'streaming' ? '正在推演' : '完成'
              }}</span>
            </div>
            <MessageAssets
              v-if="message.role === 'user' && message.assets?.length"
              :assets="message.assets"
              :user-id="userId"
            />
            <template v-if="message.role === 'assistant' && message.timeline?.length">
              <template v-for="(event, index) in message.timeline" :key="index">
                <details v-if="event.type === 'reasoning_summary'" class="reasoning">
                  <summary>推理摘要</summary>
                  <div
                    class="reasoning-markdown markdown"
                    v-html="renderReasoningMarkdown(event.content || '')"
                  ></div>
                </details>
                <ToolEventDetails
                  v-else-if="event.type === 'tool_started' || event.type === 'tool_finished'"
                  :type="event.type"
                  :tool="event.tool"
                  :content="event.content"
                />
                <TimelineCard
                  v-else-if="event.type === 'card'"
                  :kind="event.kind"
                  :payload="timelineCardPayload(message, event.payload)"
                  @play-bilibili="openBilibiliVideo"
                />
                <div
                  v-else
                  class="message-content markdown"
                  v-html="renderTimelineMarkdown(message, event.content || '')"
                ></div>
                <b
                  v-if="message.status === 'streaming' && index === message.timeline.length - 1"
                  class="cursor"
                ></b>
              </template>
            </template>
            <template v-else>
              <details v-if="message.reasoning_summary" class="reasoning">
                <summary>推理摘要</summary>
                <div
                  class="reasoning-markdown markdown"
                  v-html="renderReasoningMarkdown(message.reasoning_summary)"
                ></div>
              </details>
              <ToolEventDetails
                v-for="(event, index) in message.tool_events"
                :key="index"
                :type="event.type === 'tool_finished' ? 'tool_finished' : 'tool_started'"
                :tool="typeof event.tool === 'string' ? event.tool : undefined"
                :content="typeof event.content === 'string' ? event.content : undefined"
              />
              <template v-if="message.role === 'user' && editingMessageId === message.id">
                <textarea
                  v-model="editingMessageContent"
                  class="message-edit"
                  rows="3"
                  @keydown.esc="cancelMessageEdit"
                ></textarea>
                <div class="message-edit-actions">
                  <button @click="cancelMessageEdit">取消</button
                  ><button
                    class="primary"
                    :disabled="!editingMessageContent.trim()"
                    @click="saveMessageEdit(message)"
                  >
                    保存并重试
                  </button>
                </div>
              </template>
              <div
                v-else
                class="message-content markdown"
                v-html="renderMarkdown(message.content)"
              ></div>
              <b v-if="message.status === 'streaming'" class="cursor"></b>
            </template>
            <div v-if="message.status !== 'streaming'" class="message-actions">
              <button
                v-if="message.role === 'user'"
                title="编辑后重新生成"
                @click="beginMessageEdit(message)"
              >
                编辑
              </button>
              <button v-else title="重新生成此回答" @click="retryMessage(message)">重试</button>
              <button v-if="message.role === 'assistant'" title="复制原始 Markdown" @click="copyReply(message)">
                {{ copiedMessageId === message.id ? '已复制' : '复制 MD' }}
              </button>
              <button title="从这里创建新会话" @click="branchFrom(message)">创建分支</button>
              <span v-if="(message.sibling_count || 1) > 1" class="version-switch">
                <button
                  :disabled="!message.sibling_index"
                  title="上一个版本"
                  @click="selectVersion(message, -1)"
                >
                  ‹
                </button>
                <b>{{ (message.sibling_index || 0) + 1 }} / {{ message.sibling_count }}</b>
                <button
                  :disabled="(message.sibling_index || 0) >= (message.sibling_count || 1) - 1"
                  title="下一个版本"
                  @click="selectVersion(message, 1)"
                >
                  ›
                </button>
              </span>
            </div>
          </div>
        </article>
      </section>

      <aside v-if="conversationTurns.length" class="message-navigator" aria-label="对话轮次预览">
        <div
          class="navigator-track"
          :style="{ height: `${Math.min(560, Math.max(64, conversationTurns.length * 24))}px` }"
        >
          <button
            v-for="(turn, index) in conversationTurns"
            :key="turn.user?.id || turn.assistant?.id || index"
            class="navigator-stop"
            :class="{
              active: previewTurn === index,
              pending: turn.assistant?.status === 'streaming',
            }"
            :aria-label="`查看第 ${index + 1} 轮对话`"
            @mouseenter="previewTurn = index"
            @mouseleave="previewTurn = -1"
            @focus="previewTurn = index"
            @blur="previewTurn = -1"
          >
            <span class="navigator-mark"></span>
            <div v-if="previewTurn === index" class="turn-preview" role="tooltip">
              <div class="preview-question">
                <span>YOU</span>
                <p>{{ previewText(turn.user) }}</p>
              </div>
              <div class="preview-answer">
                <span>{{ modelLabel }}</span>
                <p>{{ previewText(turn.assistant) }}</p>
              </div>
            </div>
          </button>
        </div>
      </aside>

      <footer class="composer-wrap">
        <p v-if="chat.error" class="error-line">{{ chat.error }}</p>
        <div v-if="player.state.currentTrack" class="player-dock">
          <div class="player-cover">
            <img
              v-if="player.state.currentTrack.cover_url"
              :src="player.state.currentTrack.cover_url"
              alt=""
            /><span v-else>♪</span>
          </div>
          <div class="player-copy">
            <span>NOW {{ player.state.playing ? 'PLAYING' : 'PAUSED' }}</span>
            <strong>{{ player.state.currentTrack.name }}</strong>
            <small>{{ player.state.currentTrack.artists.join(' / ') }}</small>
          </div>
          <i v-if="player.state.playing" class="dock-wave"><b></b><b></b><b></b><b></b></i>
          <button @click="player.toggle(player.state.currentTrack)">
            {{ player.state.playing ? 'Ⅱ' : '▶' }}
          </button>
        </div>
        <p v-if="player.state.error" class="player-error">{{ player.state.error }}</p>
        <div class="composer">
          <AttachmentComposer
            v-model="pendingAssets"
            :user-id="userId"
            :disabled="chat.generating"
            @busy="attachmentBusy = $event"
          />
          <textarea
            v-model="input"
            rows="1"
            placeholder="输入任务、问题或下一步…"
            @keydown="keydown"
          ></textarea>
          <div class="composer-actions">
            <div class="composer-meta">
              <div
                v-if="showThinkingControl"
                class="thinking-control"
                role="group"
                aria-label="推理强度"
              >
                <span>THINK</span>
                <button
                  v-for="option in thinkingLevels"
                  :key="option.value"
                  type="button"
                  :class="{ active: chat.preferences.thinkingLevel === option.value }"
                  :aria-pressed="chat.preferences.thinkingLevel === option.value"
                  @click="chat.preferences.thinkingLevel = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
              <span class="composer-hint">Shift ↵ 换行</span>
            </div>
            <button v-if="chat.activeGenerating" class="stop" @click="chat.stop">■ 停止</button
            ><button
              v-else
              class="send"
              :disabled="chat.generating || attachmentBusy || (!input.trim() && !pendingAssets.length)"
              @click="send"
            >→</button>
          </div>
        </div>
        <p class="disclaimer">OBSIDIAN 可以调用已连接的能力；请核对执行结果。</p>
      </footer>
    </main>
    <BilibiliPlayerModal :video="activeBilibiliVideo" @close="activeBilibiliVideo = null" />
    <div v-if="profileOpen" class="profile-backdrop" @click.self="profileOpen = false">
      <section class="profile-panel">
        <button class="close-panel" @click="profileOpen = false">×</button>
        <p class="serial">PERSONAL NODE</p>
        <div class="profile-hero">
          <img v-if="profile?.avatar_data_url" :src="profile.avatar_data_url" alt="" /><span
            v-else
            >{{ userInitials }}</span
          >
        </div>
        <h2>{{ userName }}</h2>
        <p>{{ profile?.email || userId }}</p>
        <ImageSourcePicker
          :model-value="profile?.avatar_data_url"
          :user-id="userId"
          :provider-id="chat.preferences.providerId"
          scope-id="user-avatar"
          theme="light"
          shape="circle"
          :disabled="profileBusy"
          :allow-remove="false"
          @update:model-value="saveProfileAvatar"
          @error="profileError = $event"
        />
        <p v-if="profileError" class="profile-error">{{ profileError }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&display=swap');
.workbench {
  --ink: #111;
  --paper: #ece9e2;
  --cream: #f7f5f0;
  --acid: #d9ff36;
  --line: rgba(17, 17, 17, 0.13);
  height: 100dvh;
  overflow: hidden;
  background: var(--paper);
  color: var(--ink);
  display: grid;
  grid-template-columns: 286px minmax(0, 1fr);
  font-family: Manrope, sans-serif;
  position: relative;
}
.workbench:before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.4;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.025) 1px, transparent 1px);
  background-size: 32px 32px;
}
.rail {
  z-index: 2;
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
  background: #171717;
  color: #f1efe8;
  padding: 28px 18px 20px;
  display: flex;
  flex-direction: column;
}
.rail-brand {
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  letter-spacing: 0.13em;
  font-size: 13px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 10px 30px;
}
.rail-brand:focus-visible { outline: 1px solid var(--acid); outline-offset: -4px; }
.rail-brand i {
  font-style: normal;
  color: var(--acid);
}
.brand-orbit {
  height: 17px;
  width: 17px;
  border: 2px solid var(--acid);
  border-radius: 50%;
  position: relative;
}
.brand-orbit:after {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 50%;
  background: var(--acid);
}
.rail-mode-switcher {
  flex: 0 0 auto;
  margin: -15px 0 14px;
}
.new-session {
  border: 1px solid rgba(255, 255, 255, 0.27);
  background: transparent;
  color: #fff;
  padding: 13px 12px;
  text-align: left;
  font: 600 13px Manrope;
  cursor: pointer;
  transition: 0.25s;
  margin-bottom: 30px;
}
.new-session span {
  color: var(--acid);
  font-size: 20px;
  line-height: 0;
  vertical-align: -2px;
  margin-right: 8px;
}
.new-session kbd {
  float: right;
  color: #838383;
  font: 10px 'DM Mono';
  padding-top: 4px;
}
.new-session:hover {
  background: var(--acid);
  color: #111;
  border-color: var(--acid);
}
.assistant-switch {
  position: relative;
  margin: -14px 0 24px;
}
.assistant-current {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: 30px 1fr auto;
  grid-template-rows: auto auto;
  gap: 1px 9px;
  align-items: center;
  border: 1px solid #353535;
  background: #202020;
  color: #eee;
  padding: 8px;
  text-align: left;
  cursor: pointer;
}
.assistant-current img,
.assistant-current > span {
  grid-row: 1/3;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  object-fit: cover;
  background: var(--acid);
  color: #111;
  display: grid;
  place-items: center;
  font: 9px 'DM Mono';
}
.assistant-current small {
  font: 8px 'DM Mono';
  letter-spacing: 0.1em;
  color: #858585;
}
.assistant-current strong {
  font: 11px Manrope;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.assistant-current b {
  grid-column: 3;
  grid-row: 1/3;
  font-size: 14px;
  font-weight: 400;
}
.assistant-menu {
  position: absolute;
  z-index: 12;
  left: 0;
  right: 0;
  top: calc(100% + 5px);
  padding: 5px;
  background: #282828;
  border: 1px solid #505050;
  box-shadow: 8px 8px 0 #111;
}
.assistant-menu button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  color: #c9c9c5;
  padding: 8px;
  text-align: left;
  font: 11px Manrope;
  cursor: pointer;
}
.assistant-menu button:hover,
.assistant-menu button.active {
  background: #3a3a3a;
  color: #fff;
}
.assistant-menu img,
.assistant-menu span {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  object-fit: cover;
  background: var(--acid);
  color: #111;
  display: grid;
  place-items: center;
  font: 8px 'DM Mono';
}
.assistant-menu .assistant-manage {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid #4a4a4a;
  color: var(--acid);
}
.rail-label,
.head-eyebrow,
.serial {
  font: 10px 'DM Mono';
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.rail-label {
  color: #777;
  padding: 0 10px 10px;
}
.conversation-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: #555a52 #1d1d1d;
  scrollbar-gutter: stable;
}
.conversation-list::-webkit-scrollbar {
  width: 6px;
}
.conversation-list::-webkit-scrollbar-track {
  background: #1d1d1d;
  border-left: 1px solid #292929;
}
.conversation-list::-webkit-scrollbar-thumb {
  min-height: 34px;
  background: #51564e;
  border: 1px solid #1d1d1d;
  border-radius: 0;
}
.conversation-list::-webkit-scrollbar-thumb:hover {
  background: var(--acid);
}
.conversation-row {
  display: flex;
  align-items: center;
  min-width: 0;
}
.conversation-main {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  border: 0;
  background: transparent;
  color: #a9a9a9;
  padding: 10px;
  text-align: left;
  font: 500 12px Manrope;
  cursor: pointer;
  transition: 0.2s;
}
.conversation-row:hover .conversation-main,
.conversation-row.active .conversation-main {
  background: #2a2a2a;
  color: #fff;
}
.conversation-signal {
  width: 5px;
  height: 5px;
  background: #555;
  border-radius: 50%;
  flex: none;
}
.active .conversation-signal {
  background: var(--acid);
  box-shadow: 0 0 8px var(--acid);
}
.conversation-row.generating .conversation-signal {
  background: #ffb84c;
  box-shadow: 0 0 0 3px rgba(255, 184, 76, 0.12);
  animation: conversationPulse 1.1s ease-in-out infinite;
}
.conversation-row.generating.active .conversation-signal {
  background: var(--acid);
}
.generating-label {
  color: #ffcb72 !important;
}
@keyframes conversationPulse {
  50% {
    opacity: 0.3;
    transform: scale(0.72);
  }
}
.conversation-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.conversation-actions {
  display: flex;
  opacity: 0;
  transition: 0.2s;
}
.conversation-row:hover .conversation-actions,
.conversation-row.active .conversation-actions {
  opacity: 1;
}
.conversation-actions button {
  border: 0;
  background: transparent;
  color: #929292;
  cursor: pointer;
  font-size: 15px;
  padding: 5px;
}
.conversation-actions button:hover {
  color: var(--acid);
}
.rename-input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 1px solid var(--acid);
  background: #333;
  color: #fff;
  padding: 3px 5px;
  font: 500 12px Manrope;
}
.empty-list {
  color: #666;
  text-align: center;
  padding: 35px 0;
  font: 11px/1.8 'DM Mono';
}
.rail-footer {
  border-top: 1px solid #333;
  padding-top: 12px;
  display: grid;
  gap: 4px;
}
.rail-footer > button {
  background: transparent;
  border: 0;
  color: #999;
  padding: 8px;
  text-align: left;
  font: 11px Manrope;
  cursor: pointer;
}
.rail-footer > button:hover {
  color: var(--acid);
}
.user-card {
  display: grid;
  grid-template-columns: 30px 1fr auto;
  align-items: center;
  gap: 9px;
  margin-bottom: 5px;
}
.user-card img,
.user-initials {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--acid);
  color: #111;
  display: grid;
  place-items: center;
  font: 9px 'DM Mono';
}
.user-card strong,
.user-card small {
  display: block;
  max-width: 170px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-card strong {
  font-size: 11px;
  color: #e9e8df;
}
.user-card small {
  font: 9px 'DM Mono';
  color: #777;
  margin-top: 2px;
}
.user-card b {
  font-size: 16px;
  font-weight: 400;
}
.dialogue {
  z-index: 1;
  min-width: 0;
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: 82px minmax(0, 1fr) auto;
}
.dialogue-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--line);
  padding: 0 42px;
  background: rgba(247, 245, 240, 0.55);
  backdrop-filter: blur(16px);
}
.head-context {
  display: grid;
  gap: 2px;
}
.head-eyebrow {
  color: #7b7a76;
}
.head-context strong {
  font-size: 14px;
  letter-spacing: -0.02em;
}
.model-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  background: var(--cream);
  padding: 5px 11px 5px 5px;
  border-radius: 30px;
  font: 11px 'DM Mono';
  cursor: pointer;
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #31b45f;
  box-shadow: 0 0 0 3px rgba(49, 180, 95, 0.14);
}
.model-chip i {
  font-style: normal;
  margin-left: 2px;
}
.mobile-menu {
  display: none;
}
.timeline {
  min-height: 0;
  overflow: auto;
  padding: 52px clamp(24px, 8vw, 130px) 28px;
  scroll-behavior: smooth;
}
.welcome {
  max-width: 735px;
  animation: rise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.serial {
  color: #777;
  margin-bottom: 25px;
}
.welcome h1 {
  font: 700 clamp(48px, 7vw, 98px)/0.92 'Playfair Display';
  letter-spacing: -0.07em;
  margin: 0;
}
.welcome h1 em {
  font-weight: 600;
  color: #777;
}
.welcome > p:not(.serial) {
  max-width: 400px;
  margin: 27px 0 36px;
  color: #585752;
  line-height: 1.7;
  font-size: 14px;
}
.prompt-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.prompt-grid button {
  background: rgba(255, 255, 255, 0.38);
  border: 1px solid var(--line);
  padding: 17px 14px;
  text-align: left;
  font: 600 12px/1.4 Manrope;
  cursor: pointer;
  min-height: 84px;
  transition: 0.25s;
}
.prompt-grid button:hover {
  background: var(--acid);
  transform: translateY(-3px);
  box-shadow: 4px 5px 0 #111;
}
.prompt-grid span {
  display: block;
  margin-top: 11px;
  font-size: 15px;
}
.message {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 16px;
  max-width: 810px;
  margin: 0 auto 35px;
  animation: rise 0.35s ease both;
}
.avatar {
  height: 31px;
  width: 31px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #171717;
  color: var(--acid);
  overflow: visible;
}
.avatar > img {
  width: 31px;
  height: 31px;
  border-radius: 50%;
  object-fit: cover;
}
.avatar > span {
  font: 9px 'DM Mono';
  background: var(--acid);
  color: #111;
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border-radius: 50%;
}
.avatar :deep(.model-avatar) {
  width: 31px;
  height: 31px;
  border-radius: 50%;
  box-shadow: none;
  clip-path: none;
}
.message-meta {
  font: 10px 'DM Mono';
  letter-spacing: 0.1em;
  margin: 5px 0 10px;
}
.message-meta span {
  color: #888;
  margin-left: 7px;
}
.message-content {
  white-space: pre-wrap;
  margin: 0;
  font-size: 14px;
  line-height: 1.85;
  letter-spacing: -0.01em;
}
.message.user .message-content {
  font-weight: 600;
}
.reasoning {
  margin: 0 0 10px;
  border-left: 2px solid #a0a099;
  padding: 8px 11px;
  background: rgba(0, 0, 0, 0.035);
  font: 11px/1.6 'DM Mono';
  color: #666;
}
.reasoning summary {
  cursor: pointer;
  color: #333;
}
.reasoning p {
  margin: 6px 0 0;
}
.reasoning-markdown {
  margin-top: 8px;
  font: 11px/1.7 'DM Mono';
  color: #666;
}
.reasoning-markdown :deep(p) {
  margin: 5px 0 0;
}
.reasoning-markdown :deep(h1),
.reasoning-markdown :deep(h2),
.reasoning-markdown :deep(h3) {
  margin: 11px 0 4px;
  color: #1d1d1b;
  font: 700 11px/1.4 Manrope;
  letter-spacing: 0.02em;
}
.reasoning-markdown :deep(h1:first-child),
.reasoning-markdown :deep(h2:first-child),
.reasoning-markdown :deep(h3:first-child) {
  margin-top: 2px;
}
.cursor {
  display: inline-block;
  width: 7px;
  height: 16px;
  background: #111;
  margin-left: 4px;
  vertical-align: -3px;
  animation: blink 0.8s step-end infinite;
}
.player-dock {
  position: relative;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto 34px;
  align-items: center;
  gap: 11px;
  width: min(100%, 530px);
  margin: 0 auto 10px;
  padding: 8px 10px 8px 8px;
  border: 1px solid #1b1b1b;
  background: #1b1b1b;
  color: #efede5;
  box-shadow: 4px 4px 0 var(--acid);
  animation: player-arrive 0.32s cubic-bezier(0.2, 0.85, 0.25, 1);
}
.player-dock::after {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(90deg, transparent 0 18px, rgb(255 255 255 / 0.025) 18px 19px);
  content: '';
  pointer-events: none;
}
.player-cover {
  z-index: 1;
  width: 42px;
  height: 42px;
  overflow: hidden;
  display: grid;
  place-items: center;
  background: var(--acid);
  color: #111;
  font: 20px Georgia;
}
.player-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.player-copy {
  z-index: 1;
  display: grid;
  min-width: 0;
}
.player-copy span {
  color: var(--acid);
  font: 7px 'DM Mono';
  letter-spacing: 0.16em;
}
.player-copy strong,
.player-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.player-copy strong {
  margin-top: 2px;
  font: 700 11px Manrope;
}
.player-copy small {
  color: #88857e;
  font: 8px 'DM Mono';
}
.player-dock > button {
  z-index: 1;
  width: 32px;
  height: 32px;
  border: 1px solid #68665f;
  border-radius: 50%;
  background: transparent;
  color: var(--acid);
  cursor: pointer;
}
.dock-wave {
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 2px;
  height: 18px;
}
.dock-wave b {
  width: 2px;
  height: 6px;
  background: var(--acid);
  animation: dock-meter 0.7s ease-in-out infinite alternate;
}
.dock-wave b:nth-child(2) { animation-delay: -0.45s; }
.dock-wave b:nth-child(3) { animation-delay: -0.2s; }
.dock-wave b:nth-child(4) { animation-delay: -0.6s; }
.player-error {
  width: min(100%, 530px);
  margin: 0 auto 8px;
  color: #a33e34;
  font: 8px 'DM Mono';
}
@keyframes dock-meter { to { height: 18px; } }
@keyframes player-arrive {
  from { opacity: 0; transform: translateY(8px); }
}
.composer-wrap {
  padding: 0 clamp(24px, 8vw, 130px) 22px;
  background: linear-gradient(transparent, var(--paper) 18%);
}
.composer {
  border: 1px solid #1b1b1b;
  background: #fdfcf9;
  padding: 15px 16px 10px;
  box-shadow: 6px 6px 0 #1b1b1b;
  transition: 0.25s;
}
.composer:focus-within {
  box-shadow: 9px 9px 0 var(--acid);
  transform: translate(-2px, -2px);
}
textarea {
  display: block;
  width: 100%;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  font: 500 14px/1.6 Manrope;
  min-height: 28px;
  max-height: 160px;
}
.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 9px;
  color: #8b8983;
  font: 9px 'DM Mono';
}
.composer-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.thinking-control {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid rgba(27, 27, 27, 0.2);
  background: #f1efe9;
}
.thinking-control > span {
  padding: 0 5px;
  color: #5d5b55;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.thinking-control button {
  min-width: 25px;
  border: 0;
  padding: 4px 6px;
  background: transparent;
  color: #77746c;
  cursor: pointer;
  font: 700 9px 'DM Mono';
  transition: background 0.16s ease, color 0.16s ease, transform 0.16s ease;
}
.thinking-control button:hover {
  color: #111;
}
.thinking-control button.active {
  background: #1b1b1b;
  color: var(--acid);
  transform: translateY(-1px);
}
.send,
.stop {
  border: 0;
  cursor: pointer;
  font: 700 15px Manrope;
  padding: 5px 11px;
  background: var(--acid);
  color: #111;
}
.send:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.stop {
  font-size: 10px;
  background: #1b1b1b;
  color: #fff;
}
.disclaimer {
  font: 9px 'DM Mono';
  color: #898783;
  text-align: center;
  margin: 14px 0 0;
}
.error-line,
.profile-error {
  color: #b24038;
  font: 11px 'DM Mono';
  margin: 0 0 8px;
}
.profile-backdrop {
  position: fixed;
  z-index: 20;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  padding: 20px;
  backdrop-filter: blur(8px);
}
.profile-panel {
  position: relative;
  width: min(100%, 380px);
  padding: 36px;
  background: #f8f6ef;
  box-shadow: 12px 12px 0 #111;
  text-align: center;
}
.close-panel {
  position: absolute;
  right: 12px;
  top: 8px;
  background: transparent;
  border: 0;
  font-size: 25px;
  cursor: pointer;
}
.profile-hero {
  width: 94px;
  height: 94px;
  margin: 0 auto 18px;
  border: 3px solid #111;
  box-shadow: 5px 5px 0 var(--acid);
  overflow: hidden;
  background: #171717;
  color: var(--acid);
  display: grid;
  place-items: center;
  font: 28px 'DM Mono';
}
.profile-hero img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.profile-panel h2 {
  margin: 0;
  font: 700 31px 'Playfair Display';
}
.profile-panel > p:not(.serial):not(.profile-error) {
  margin: 6px 0 25px;
  color: #777;
  font-size: 12px;
}
.avatar-upload {
  display: inline-block;
  background: var(--acid);
  border: 1px solid #111;
  padding: 10px 16px;
  font: 700 12px Manrope;
  cursor: pointer;
}
.avatar-upload input {
  display: none;
}
.profile-panel small {
  display: block;
  margin-top: 11px;
  color: #777;
  font: 9px 'DM Mono';
}
.profile-error {
  margin: 14px 0 0;
}
.markdown :deep(p) {
  margin: 0 0 12px;
}
.markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown :deep(h1),
.markdown :deep(h2),
.markdown :deep(h3),
.markdown :deep(h4) {
  margin: 22px 0 10px;
  line-height: 1.2;
  letter-spacing: -0.03em;
}
.markdown :deep(h1) {
  font-size: 1.55em;
}
.markdown :deep(h2) {
  font-size: 1.3em;
}
.markdown :deep(h3) {
  font-size: 1.12em;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 8px 0 13px;
  padding-left: 24px;
}
.markdown :deep(li + li) {
  margin-top: 4px;
}
.markdown :deep(blockquote) {
  margin: 12px 0;
  padding: 7px 13px;
  border-left: 3px solid var(--acid);
  background: rgba(0, 0, 0, 0.045);
  color: #575650;
}
.markdown :deep(pre) {
  margin: 14px 0;
  padding: 14px;
  overflow: auto;
  background: #171717;
  color: #f6f5ee;
  border-radius: 2px;
  font:
    12px/1.65 'DM Mono',
    monospace;
}
.markdown :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
}
.markdown :deep(code) {
  padding: 2px 5px;
  background: rgba(17, 17, 17, 0.1);
  font:
    12px 'DM Mono',
    monospace;
}
.markdown :deep(a) {
  color: #456d00;
  text-decoration: underline;
  text-decoration-color: var(--acid);
  text-underline-offset: 3px;
}
.markdown :deep(img) {
  display: block;
  width: auto;
  height: auto;
  max-width: min(100%, 640px);
  max-height: 70vh;
  object-fit: contain;
}
.markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 13px 0;
  font-size: 12px;
}
.markdown :deep(th),
.markdown :deep(td) {
  padding: 7px 9px;
  border: 1px solid var(--line);
  text-align: left;
}
.markdown :deep(th) {
  background: rgba(0, 0, 0, 0.055);
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
@media (max-width: 760px) {
  .workbench {
    grid-template-columns: 1fr;
  }
  .rail {
    position: fixed;
    inset: 0 auto 0 0;
    width: 280px;
    transform: translateX(-102%);
    transition: 0.3s;
    box-shadow: 20px 0 50px rgba(0, 0, 0, 0.2);
  }
  .sidebar-open .rail {
    transform: none;
  }
  .dialogue-head {
    padding: 0 20px;
  }
  .mobile-menu {
    display: block;
    border: 0;
    background: transparent;
    font-size: 19px;
  }
  .timeline {
    padding: 35px 20px 20px;
  }
  .composer-wrap {
    padding: 0 22px 20px;
  }
  .composer-hint {
    display: none;
  }
  .prompt-grid {
    grid-template-columns: 1fr;
  }
  .welcome h1 {
    font-size: 58px;
  }
  .model-chip {
    max-width: 180px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
}
.dialogue {
  position: relative;
}
.message-navigator {
  position: absolute;
  z-index: 4;
  left: 13px;
  top: 50%;
  width: 30px;
  transform: translateY(-50%);
  pointer-events: none;
}
.navigator-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 5px 0;
}
.navigator-stop {
  position: relative;
  display: grid;
  place-items: center;
  flex: 1 1 0;
  min-height: 4px;
  width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: default;
  pointer-events: auto;
}
.navigator-mark {
  height: 2px;
  width: 9px;
  background: #b8b6b0;
  transition:
    width 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}
.navigator-stop:hover .navigator-mark,
.navigator-stop:focus-visible .navigator-mark,
.navigator-stop.active .navigator-mark {
  width: 21px;
  background: #191919;
  transform: translateX(5px);
}
.navigator-stop.pending .navigator-mark {
  background: #6d6c66;
  animation: marker-pulse 0.85s ease-in-out infinite;
}
.navigator-stop:focus-visible {
  outline: 0;
}
.turn-preview {
  position: absolute;
  z-index: 5;
  left: 32px;
  top: 50%;
  width: min(390px, calc(100vw - 390px));
  max-height: 210px;
  overflow: hidden;
  transform: translateY(-50%);
  border: 1px solid rgba(17, 17, 17, 0.13);
  border-radius: 20px;
  background: rgba(253, 252, 249, 0.97);
  box-shadow:
    0 15px 34px rgba(17, 17, 17, 0.13),
    0 2px 8px rgba(17, 17, 17, 0.06);
  padding: 16px 17px;
  text-align: left;
  backdrop-filter: blur(14px);
  cursor: default;
  animation: preview-in 0.18s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.turn-preview:before {
  content: '';
  position: absolute;
  left: -5px;
  top: 50%;
  width: 9px;
  height: 9px;
  background: #fdfcf9;
  border-left: 1px solid rgba(17, 17, 17, 0.13);
  border-bottom: 1px solid rgba(17, 17, 17, 0.13);
  transform: translateY(-50%) rotate(45deg);
}
.preview-question,
.preview-answer {
  position: relative;
}
.preview-question {
  padding-bottom: 11px;
  border-bottom: 1px solid rgba(17, 17, 17, 0.09);
}
.preview-answer {
  padding-top: 11px;
}
.preview-question span,
.preview-answer span {
  display: block;
  margin-bottom: 4px;
  color: #8c8a84;
  font: 9px 'DM Mono';
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.preview-answer span {
  color: #5a7117;
}
.preview-question p,
.preview-answer p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: #242321;
  font: 600 13px/1.45 Manrope;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.preview-answer p {
  font-weight: 500;
  color: #77756f;
}
@keyframes marker-pulse {
  50% {
    opacity: 0.35;
    transform: scaleX(0.65);
  }
}
@keyframes preview-in {
  from {
    opacity: 0;
    transform: translate(-5px, -50%);
  }
  to {
    opacity: 1;
    transform: translateY(-50%);
  }
}
@media (max-width: 900px) {
  .message-navigator {
    display: none;
  }
}
.conversation-copy {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 3px;
}
.conversation-date {
  color: #777;
  font: 9px 'DM Mono';
  letter-spacing: 0.03em;
}
.conversation-row.active .conversation-date {
  color: #9e9e9a;
}
.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.message-meta strong {
  font: inherit;
  font-weight: 500;
}
.message-time {
  color: #8d8b85;
  font: 9px 'DM Mono';
  letter-spacing: 0.04em;
}
.message-status {
  margin-left: 0 !important;
}
.message-status:before {
  content: '·';
  margin-right: 8px;
  color: #aaa8a2;
}
.message-actions {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 13px;
  opacity: 0;
  transition: opacity 0.18s;
}
.message:hover .message-actions {
  opacity: 1;
}
.message-actions button,
.message-edit-actions button {
  border: 1px solid transparent;
  background: transparent;
  color: #777;
  padding: 3px 6px;
  font: 10px 'DM Mono';
  cursor: pointer;
}
.message-actions button:hover,
.message-edit-actions button:hover {
  border-color: var(--line);
  background: #fff;
  color: #111;
}
.message-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.3;
}
.version-switch {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-left: 3px;
  padding-left: 5px;
  border-left: 1px solid var(--line);
}
.version-switch b {
  min-width: 31px;
  text-align: center;
  color: #555;
  font: 9px 'DM Mono';
}
.message-edit {
  width: 100%;
  margin: 0;
  border: 1px solid #191919;
  outline: 0;
  background: #fffdf7;
  padding: 9px 10px;
  font: 500 13px/1.65 Manrope;
  resize: vertical;
}
.message-edit:focus {
  box-shadow: 3px 3px 0 var(--acid);
}
.message-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 7px;
}
.message-edit-actions .primary {
  border-color: #171717;
  background: var(--acid);
  color: #111;
}
.message.user .message-actions {
  justify-content: flex-end;
}
.sync-indicator {
  position: fixed;
  z-index: 50;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(236, 233, 226, 0.52);
  backdrop-filter: blur(2px);
  font: 600 11px 'DM Mono';
  letter-spacing: 0.08em;
  color: #242321;
}
.sync-indicator span {
  padding: 10px 14px;
  background: #171717;
  color: #f7f5f0;
  box-shadow: 4px 4px 0 var(--acid);
}
.sync-indicator i {
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid #171717;
  border-right-color: transparent;
  border-radius: 50%;
  animation: sync-spin 0.72s linear infinite;
  transform: translateX(-78px);
}
@keyframes sync-spin {
  to {
    transform: translateX(-78px) rotate(360deg);
  }
}
</style>
