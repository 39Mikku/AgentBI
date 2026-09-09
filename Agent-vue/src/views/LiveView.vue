<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import type { LiveModelId } from '@/api/live-types'
import { listTtsVoices } from '@/api/toolbox-tts'
import type { TtsCustomVoice } from '@/api/toolbox-tts-types'
import AppModeSwitcher from '@/components/AppModeSwitcher.vue'
import BrandMark from '@/components/brand/BrandMark.vue'
import ImageSourcePicker from '@/components/ImageSourcePicker.vue'
import WorkspaceRailToggle from '@/components/WorkspaceRailToggle.vue'
import { getPreferences as getChatPreferences } from '@/api/chat'
import LiveAvatarCore from '@/components/live/LiveAvatarCore.vue'
import {
  historySliderToTurns,
  historyTurnsLabel,
  historyTurnsToSlider,
} from '@/live/history-context'
import { isLiveVoiceCompatible, roleInitials, voiceLabel } from '@/live/role-presentation'
import { useWorkspaceStore } from '@/stores/workspace'
import { useLiveStore } from '@/stores/live'
import { availableLiveVoices } from '@/toolbox/voice-workbench'
import { useWorkspaceRail } from '@/composables/useWorkspaceRail'

const workspace = useWorkspaceStore()
const live = useLiveStore()
const router = useRouter()
const userId = computed(() => workspace.userId)
const userName = computed(() => workspace.profile?.username || userId.value.split('@')[0] || userId.value)
const userInitials = computed(() => roleInitials(userName.value))
const modelTier = computed(() => live.preferences.model.endsWith('plus') ? 'PLUS' : 'FLASH')
const phaseCode = computed(() => live.state.phase.toUpperCase().padEnd(10, '·'))
const roleName = computed(() => live.currentRole?.name || 'Live Assistant')
const { railCollapsed, toggleRail } = useWorkspaceRail()

const settingsOpen = ref(false)
const settingsTab = ref<'call' | 'role' | 'memory'>('call')
const roleMenuOpen = ref(false)
const transcriptRail = ref<HTMLElement | null>(null)
const editingConversationId = ref('')
const editingTitle = ref('')
const memoryDraft = ref('')
const imageProviderId = ref<string>()
const callDurationLabel = ref('00:00')
const customVoice = ref('')
const voiceMode = ref('builtin')
const customVoices = ref<TtsCustomVoice[]>([])
let durationTimer: ReturnType<typeof setInterval> | null = null
let startedAt = 0

const roleDraft = reactive({
  name: '',
  instructions: '',
  voice: 'longanqian',
  avatar_data_url: null as string | null,
  memory_enabled: false,
})

const models: Array<{ id: LiveModelId; label: string; note: string }> = [
  { id: 'qwen-audio-3.0-realtime-flash', label: 'Flash', note: '低延迟，适合自然闲聊' },
  { id: 'qwen-audio-3.0-realtime-plus', label: 'Plus', note: '更强理解与复杂表达' },
]
const voices = [
  { id: 'longanqian', label: '芊悦', code: 'QIAN' },
  { id: 'longanlingxin', label: '灵心', code: 'LINGXIN' },
  { id: 'longanlingxi', label: '灵犀', code: 'LINGXI' },
  { id: 'longanxiaoxin', label: '小新', code: 'XIAOXIN' },
  { id: 'longanlufeng', label: '鹿风', code: 'LUFENG' },
]
const builtInVoiceIds = new Set(voices.map((voice) => voice.id))
const compatibleLiveVoices = computed(() =>
  availableLiveVoices(live.preferences.model, customVoices.value),
)
const currentVoiceCompatible = computed(() =>
  !live.currentRole
  || isLiveVoiceCompatible(live.currentRole.voice, live.preferences.model, customVoices.value),
)
const draftVoiceCompatible = computed(() =>
  voiceMode.value !== 'custom'
  || isLiveVoiceCompatible(customVoice.value.trim(), live.preferences.model, customVoices.value),
)
const currentVoiceBinding = computed(() => customVoices.value.find((voice) =>
  voice.external_voice_id === live.currentRole?.voice
  && voice.provider_metadata.usage === 'live',
))

const historySlider = computed({
  get: () => historyTurnsToSlider(live.preferences.history_context_turns),
  set: (value: number) => { live.preferences.history_context_turns = historySliderToTurns(value) },
})

function formatConversationTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const today = new Date()
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function updateDuration() {
  const seconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000))
  callDurationLabel.value = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

function startDuration() {
  startedAt = Date.now()
  callDurationLabel.value = '00:00'
  if (durationTimer) clearInterval(durationTimer)
  durationTimer = setInterval(updateDuration, 1000)
}

function stopDuration() {
  if (durationTimer) clearInterval(durationTimer)
  durationTimer = null
  callDurationLabel.value = '00:00'
}

async function toggleCall() {
  if (live.isActive) {
    await live.endCall()
    stopDuration()
    return
  }
  if (!currentVoiceCompatible.value) return
  startDuration()
  await live.startCall(userId.value)
  if (live.state.phase === 'error') stopDuration()
}

function openSettings(tab: 'call' | 'role' | 'memory' = 'call') {
  settingsTab.value = tab
  settingsOpen.value = true
  roleMenuOpen.value = false
}

async function createRole() {
  if (!live.canEditSettings) return
  const created = await live.createRole({
    user_id: userId.value,
    name: `新角色 ${live.roles.length + 1}`,
    instructions: '你是一个自然、真诚且善于倾听的实时语音伙伴。',
    voice: 'longanqian',
    avatar_data_url: null,
    memory_enabled: false,
  })
  await live.selectRole(created.id, userId.value)
  openSettings('role')
}

async function saveRole() {
  if (!live.currentRole || !roleDraft.name.trim() || !roleDraft.instructions.trim()) return
  const voice = voiceMode.value === 'custom' ? customVoice.value.trim() : roleDraft.voice
  if (!voice || !draftVoiceCompatible.value) return
  await live.persistRole(live.currentRole.id, {
    name: roleDraft.name.trim(),
    instructions: roleDraft.instructions.trim(),
    voice,
    avatar_data_url: roleDraft.avatar_data_url,
    memory_enabled: roleDraft.memory_enabled,
  }, userId.value)
}

async function deleteCurrentRole() {
  const role = live.currentRole
  if (!role || role.is_default || !window.confirm(`删除角色“${role.name}”及其全部语音会话？`)) return
  await live.removeRole(role.id, userId.value)
}

function beginRename(id: string, title: string) {
  editingConversationId.value = id
  editingTitle.value = title
}

async function finishRename() {
  const id = editingConversationId.value
  const title = editingTitle.value.trim()
  editingConversationId.value = ''
  if (id && title) await live.renameConversation(id, title, userId.value)
}

async function deleteConversation(id: string) {
  if (!window.confirm('删除这段语音会话？')) return
  await live.removeConversation(id, userId.value)
}

async function saveMemory() { await live.persistRoleMemory(memoryDraft.value, userId.value) }

watch(
  () => live.currentRole,
  (role) => {
    if (!role) return
    Object.assign(roleDraft, {
      name: role.name,
      instructions: role.instructions,
      voice: builtInVoiceIds.has(role.voice) ? role.voice : 'longanqian',
      avatar_data_url: role.avatar_data_url,
      memory_enabled: role.memory_enabled,
    })
    voiceMode.value = builtInVoiceIds.has(role.voice) ? 'builtin' : 'custom'
    customVoice.value = builtInVoiceIds.has(role.voice) ? '' : role.voice
  },
  { immediate: true },
)

watch(() => live.roleMemory?.content, (value) => { memoryDraft.value = value || '' }, { immediate: true })
watch(
  () => live.state.transcripts.map((item) => `${item.id}:${item.text}:${item.stash}`).join('|'),
  async () => {
    await nextTick()
    transcriptRail.value?.scrollTo({ top: transcriptRail.value.scrollHeight, behavior: 'smooth' })
  },
)

onMounted(async () => {
  const [, voiceResult, preferenceResult] = await Promise.allSettled([
    live.loadWorkspace(userId.value),
    listTtsVoices(userId.value),
    getChatPreferences(userId.value),
  ])
  if (voiceResult.status === 'fulfilled') customVoices.value = voiceResult.value
  if (preferenceResult.status === 'fulfilled') imageProviderId.value = preferenceResult.value.providerId
})
onBeforeUnmount(() => {
  stopDuration()
  if (live.isActive) void live.endCall()
})
</script>

<template>
  <div class="live-shell" :class="{ 'rail-collapsed': railCollapsed }" :data-phase="live.state.phase">
    <aside class="workspace-rail">
      <WorkspaceRailToggle :collapsed="railCollapsed" @toggle="toggleRail" />
      <button class="live-brand" type="button" title="返回主页" @click="router.push('/home')"><BrandMark class="live-brand-mark" tone="inverse" /><span>AGENTBI</span><b>LIVE</b></button>
      <AppModeSwitcher active="live" :collapsed="railCollapsed" />

      <div class="rail-label"><span>当前角色</span><button :disabled="live.isActive" @click="openSettings('role')">管理</button></div>
      <div class="role-switcher-wrap">
        <button class="role-switcher" :disabled="live.isActive" @click="roleMenuOpen = !roleMenuOpen">
          <span class="mini-avatar">
            <img v-if="live.currentRole?.avatar_data_url" :src="live.currentRole.avatar_data_url" alt="" />
            <i v-else>{{ roleInitials(roleName) }}</i>
          </span>
          <span><strong>{{ roleName }}</strong><small>{{ voiceLabel(live.currentRole?.voice || '', customVoices) }} · {{ modelTier }}</small></span>
          <b>⌄</b>
        </button>
        <Transition name="pop">
          <div v-if="roleMenuOpen" class="role-menu">
            <button v-for="role in live.roles" :key="role.id" :class="{ active: role.id === live.activeRoleId }" @click="live.selectRole(role.id, userId); roleMenuOpen = false">
              <span>{{ roleInitials(role.name) }}</span><strong>{{ role.name }}</strong><i v-if="role.id === live.activeRoleId">●</i>
            </button>
            <button class="new-role" @click="createRole"><span>＋</span><strong>创建新角色</strong></button>
          </div>
        </Transition>
      </div>

      <button class="new-conversation" title="新语音会话" :disabled="live.isActive || !live.currentRole" @click="live.newConversation(userId)">
        <span>＋</span><strong>新语音会话</strong><small>NEW CALL</small>
      </button>

      <div class="rail-label conversation-label"><span>会话记录</span><small>{{ live.conversations.length }}</small></div>
      <div class="conversation-list">
        <div v-if="live.loading" class="rail-loading"><i></i><span>正在同步声场…</span></div>
        <p v-else-if="!live.conversations.length" class="empty-conversations">还没有通话记录<br /><span>开始第一段实时对话</span></p>
        <article v-for="conversation in live.conversations" :key="conversation.id" :class="{ active: conversation.id === live.activeConversationId }">
          <button class="conversation-main" :disabled="live.isActive" @click="live.selectConversation(conversation.id, userId)">
            <i></i>
            <span>
              <input v-if="editingConversationId === conversation.id" v-model="editingTitle" autofocus @click.stop @blur="finishRename" @keyup.enter="finishRename" @keyup.esc="editingConversationId = ''" />
              <strong v-else>{{ conversation.title }}</strong>
              <small>{{ formatConversationTime(conversation.last_message_at) }}</small>
            </span>
          </button>
          <div class="conversation-actions">
            <button title="重命名" @click="beginRename(conversation.id, conversation.title)">✎</button>
            <button title="删除" @click="deleteConversation(conversation.id)">×</button>
          </div>
        </article>
      </div>

      <div class="rail-profile">
        <span class="user-avatar"><img v-if="workspace.profile?.avatar_data_url" :src="workspace.profile.avatar_data_url" alt="" /><i v-else>{{ userInitials }}</i></span>
        <span><strong>{{ userName }}</strong><small>{{ userId }}</small></span>
        <button @click="openSettings('call')">⌘</button>
      </div>
    </aside>

    <main class="live-console">
      <header class="console-head">
        <div>
          <span class="eyebrow">{{ live.currentConversation?.title || 'NEW AUDIO SESSION' }}</span>
          <h1>{{ roleName }} <em>/ live</em></h1>
        </div>
        <div class="head-metrics">
          <span><i></i>{{ live.isActive ? callDurationLabel : 'STANDBY' }}</span>
          <span class="tier">{{ modelTier }}</span>
          <button @click="openSettings('call')">配置 <b>⌘</b></button>
        </div>
      </header>

      <div class="console-body">
        <section class="voice-stage">
          <div class="stage-coordinates"><span>FULL-DUPLEX / 24K</span><span>{{ phaseCode }}</span></div>
          <LiveAvatarCore :name="roleName" :avatar="live.currentRole?.avatar_data_url" :phase="live.state.phase" :muted="live.muted" />
          <div class="stage-status" aria-live="polite">
            <span class="status-pulse"></span>
            <div><small>CHANNEL STATUS</small><strong>{{ live.statusLabel }}</strong></div>
            <code>{{ live.state.phase === 'idle' ? 'READY' : phaseCode }}</code>
          </div>
          <p v-if="live.state.error" class="live-error">{{ live.state.error }}</p>
        </section>

        <section class="transcript-panel">
          <header>
            <div><span>CONVERSATION STREAM</span><strong>实时字幕与历史</strong></div>
            <small>{{ live.state.transcripts.length }} ITEMS</small>
          </header>
          <div ref="transcriptRail" class="transcript-list">
            <div v-if="!live.state.transcripts.length" class="transcript-empty">
              <i></i><span>NO SIGNAL YET</span>
              <p>开始通话后，双方字幕将在这里随声音逐字出现。继续旧会话时，历史也会保留。</p>
            </div>
            <article v-for="item in live.state.transcripts" :key="item.id" :class="[item.role, { interrupted: item.interrupted }]">
              <div class="speaker-line">
                <span>{{ item.role === 'user' ? userName : roleName }}</span>
                <code>{{ item.role === 'user' ? 'IN' : 'OUT' }}</code>
              </div>
              <p>{{ item.text }}<span v-if="item.stash" class="stash">{{ item.stash }}</span><i v-if="!item.final"></i></p>
              <small v-if="item.interrupted">INTERRUPTED / 已打断</small>
            </article>
          </div>
        </section>
      </div>

      <footer class="call-dock">
        <div class="dock-meta"><span>VOICE</span><strong>{{ voiceLabel(live.currentRole?.voice || '', customVoices) }}</strong></div>
        <div class="call-controls">
          <button class="round-control" :class="{ active: live.muted }" :disabled="!live.isActive || live.state.phase === 'ending'" @click="live.toggleMute">
            <svg viewBox="0 0 24 24"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm-7-3a7 7 0 0 0 14 0M12 18v3M8 21h8" /></svg><span>{{ live.muted ? '恢复' : '静音' }}</span>
          </button>
          <button class="call-button" :class="{ active: live.isActive }" :disabled="live.state.phase === 'connecting' || live.state.phase === 'ending' || live.loading || (!live.isActive && !currentVoiceCompatible)" @click="toggleCall">
            <span class="call-icon"><i></i></span><strong>{{ live.isActive ? '结束通话' : '开始通话' }}</strong><small>{{ live.isActive ? 'END SESSION' : 'OPEN CHANNEL' }}</small>
          </button>
          <button class="round-control" @click="openSettings('call')">
            <svg viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M10 14v6" /></svg><span>配置</span>
          </button>
        </div>
        <p v-if="!currentVoiceCompatible" class="dock-voice-warning">当前音色绑定 {{ currentVoiceBinding?.bound_model?.endsWith('plus') ? 'PLUS' : 'FLASH' }}，请切回对应模型或为角色更换音色。</p>
        <div class="dock-meta right"><span>CONTEXT</span><strong>{{ historyTurnsLabel(live.preferences.history_context_turns) }}</strong></div>
      </footer>
    </main>

    <Transition name="deck">
      <div v-if="settingsOpen" class="deck-backdrop" @click.self="settingsOpen = false">
        <aside class="settings-deck">
          <header class="deck-head"><div><span>LIVE / CONTROL DECK</span><h2>调整你的声场</h2></div><button @click="settingsOpen = false">×</button></header>
          <nav class="deck-tabs">
            <button :class="{ active: settingsTab === 'call' }" @click="settingsTab = 'call'">通话</button>
            <button :class="{ active: settingsTab === 'role' }" @click="settingsTab = 'role'">角色</button>
            <button :class="{ active: settingsTab === 'memory' }" @click="settingsTab = 'memory'">记忆</button>
          </nav>

          <div class="deck-scroll">
            <template v-if="settingsTab === 'call'">
              <section class="deck-section">
                <label><span>01</span> 实时模型</label>
                <div class="model-options">
                  <button v-for="model in models" :key="model.id" :class="{ active: live.preferences.model === model.id }" :disabled="!live.canEditSettings" @click="live.preferences.model = model.id">
                    <strong>{{ model.label }}</strong><small>{{ model.note }}</small><i></i>
                  </button>
                </div>
              </section>
              <section class="deck-section range-section">
                <label><span>02</span> 历史上下文 <b>{{ historyTurnsLabel(live.preferences.history_context_turns) }}</b></label>
                <input v-model.number="historySlider" type="range" min="0" max="100" :disabled="!live.canEditSettings" />
                <div class="range-axis"><span>1 轮</span><span>12</span><span>50</span><span>不截断</span></div>
                <p>滑块越向右增长越快；拉到末端时向百炼传入该会话的全部完整历史。</p>
              </section>
              <section class="deck-section range-section">
                <label><span>03</span> 云端保留轮次 <b>{{ live.preferences.max_history_turns }} 轮</b></label>
                <input v-model.number="live.preferences.max_history_turns" type="range" min="1" max="50" :disabled="!live.canEditSettings" />
                <div class="range-axis"><span>1</span><span>25</span><span>50</span></div>
                <p>作为百炼实时会话的 max_history_turns，控制服务端本轮连接内保留的对话长度。</p>
              </section>
              <button class="primary-action" :disabled="live.saving || !live.canEditSettings" @click="live.persistPreferences(userId)">{{ live.saving ? '正在保存…' : '保存通话配置' }}</button>
            </template>

            <template v-else-if="settingsTab === 'role'">
              <section class="role-roster">
                <button v-for="role in live.roles" :key="role.id" :class="{ active: role.id === live.activeRoleId }" :disabled="live.isActive" @click="live.selectRole(role.id, userId)">
                  <span><img v-if="role.avatar_data_url" :src="role.avatar_data_url" alt="" /><i v-else>{{ roleInitials(role.name) }}</i></span><strong>{{ role.name }}</strong>
                </button>
                <button class="add-role" :disabled="live.isActive" @click="createRole"><span>＋</span><strong>新角色</strong></button>
              </section>
              <section class="deck-section role-identity">
                <label><span>01</span> 角色身份</label>
                <ImageSourcePicker
                  v-model="roleDraft.avatar_data_url"
                  :user-id="userId"
                  :provider-id="imageProviderId"
                  scope-id="live-role-avatar"
                  theme="dark"
                  shape="circle"
                  :disabled="!live.canEditSettings"
                />
                <input v-model="roleDraft.name" class="text-input" maxlength="40" placeholder="角色名称" :disabled="!live.canEditSettings" />
              </section>
              <section class="deck-section">
                <label><span>02</span> 系统音色</label>
                <div class="voice-options">
                  <button v-for="voice in voices" :key="voice.id" :class="{ active: voiceMode === 'builtin' && roleDraft.voice === voice.id }" :disabled="!live.canEditSettings" @click="voiceMode = 'builtin'; roleDraft.voice = voice.id"><strong>{{ voice.label }}</strong><small>{{ voice.code }}</small></button>
                  <button :class="{ active: voiceMode === 'custom' }" :disabled="!live.canEditSettings" @click="voiceMode = 'custom'"><strong>自定义</strong><small>VOICE ID</small></button>
                </div>
                <div v-if="voiceMode === 'custom'" class="custom-voice-editor">
                  <label><span>已同步的 {{ modelTier }} 音色</span></label>
                  <select :value="compatibleLiveVoices.some((voice) => voice.value === customVoice) ? customVoice : ''" :disabled="!live.canEditSettings" @change="customVoice = ($event.target as HTMLSelectElement).value || customVoice">
                    <option value="">选择音色名，或在下方手动输入</option>
                    <option v-for="voice in compatibleLiveVoices" :key="voice.key" :value="voice.value">{{ voice.label }}</option>
                  </select>
                  <input v-model="customVoice" class="text-input" maxlength="256" placeholder="复刻音色或自定义 Voice ID" :disabled="!live.canEditSettings" />
                  <p v-if="!compatibleLiveVoices.length">尚无适用于 {{ modelTier }} 的复刻音色，可前往工具箱 / Voice Lab 创建。</p>
                  <p v-if="!draftVoiceCompatible" class="voice-binding-error">该已登记音色绑定了另一个实时模型，不能用于当前 {{ modelTier }}。</p>
                </div>
              </section>
              <section class="deck-section prompt-section">
                <label><span>03</span> 系统提示词 <b>{{ roleDraft.instructions.length }} / 12000</b></label>
                <textarea v-model="roleDraft.instructions" maxlength="12000" :disabled="!live.canEditSettings" placeholder="描述角色、语气、关系与回应方式…"></textarea>
              </section>
              <section class="memory-switch-row">
                <div><strong>通话后更新角色记忆</strong><small>每次通话结束后只触发一次；关闭不会删除已有记忆。</small></div>
                <button :class="{ active: roleDraft.memory_enabled }" :disabled="!live.canEditSettings" @click="roleDraft.memory_enabled = !roleDraft.memory_enabled"><i></i></button>
              </section>
              <div class="role-actions">
                <button v-if="live.currentRole && !live.currentRole.is_default" class="danger-action" :disabled="!live.canEditSettings" @click="deleteCurrentRole">删除角色</button>
                <button class="primary-action" :disabled="!live.canEditSettings || !roleDraft.name.trim() || !roleDraft.instructions.trim() || (voiceMode === 'custom' && (!customVoice.trim() || !draftVoiceCompatible))" @click="saveRole">保存角色</button>
              </div>
            </template>

            <template v-else>
              <section class="memory-hero">
                <span>{{ roleInitials(roleName) }}</span>
                <div><small>ROLE MEMORY</small><h3>{{ roleName }} 的长期记忆</h3><p>启用时在建立实时会话前作为独立系统模块注入；原始通话记录始终保留。</p></div>
              </section>
              <section class="deck-section prompt-section memory-editor">
                <label><span>01</span> 可编辑记忆 <b>{{ memoryDraft.length }} 字</b></label>
                <textarea v-model="memoryDraft" maxlength="30000" :disabled="!live.canEditSettings" placeholder="暂无记忆。可以手动填写，也可以在通话结束后自动归纳。"></textarea>
                <small v-if="live.roleMemory?.updated_at">最后更新：{{ new Date(live.roleMemory.updated_at).toLocaleString('zh-CN') }}</small>
              </section>
              <div class="memory-actions">
                <button :disabled="!live.canEditSettings" @click="live.refreshRoleMemory(userId)">从历史重新生成</button>
                <button :disabled="!live.canEditSettings || !memoryDraft" @click="live.clearRoleMemory(userId)">清空</button>
                <button class="primary-action" :disabled="!live.canEditSettings" @click="saveMemory">保存记忆</button>
              </div>
              <p class="memory-note">记忆开关位于“角色”页。关闭只停止注入和自动更新，不会清除这里的内容。</p>
            </template>
          </div>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700&family=Syne:wght@500;600;700&display=swap');
* { box-sizing: border-box; }
.live-shell { --void:#070a09; --panel:#0d1110; --panel-2:#111715; --mist:#dce8e2; --muted:#6e7974; --signal:#9fffd8; --signal-deep:#28a983; --danger:#ff7668; width:100%; height:100dvh; overflow:hidden; display:grid; grid-template-columns:286px minmax(0,1fr); color:var(--mist); background:var(--void); font-family:Manrope,sans-serif; transition:grid-template-columns .28s cubic-bezier(.2,.8,.2,1); }
.live-shell::after { content:''; position:fixed; inset:0; z-index:20; pointer-events:none; opacity:.12; background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitchTiles'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E"); mix-blend-mode:soft-light; }
button,input,textarea { font:inherit; } button { cursor:pointer; } button:disabled { cursor:not-allowed; opacity:.42; }
.workspace-rail { min-height:0; padding:24px 16px 14px; border-right:1px solid rgba(159,255,216,.11); background:#090d0c; display:flex; flex-direction:column; gap:15px; position:relative; z-index:3; transition:padding .28s cubic-bezier(.2,.8,.2,1); }
.live-brand { width:100%; border:0; background:transparent; color:inherit; display:flex; align-items:center; gap:8px; padding:0 6px 3px; font:700 var(--control-font-size) Syne; letter-spacing:.13em; }.live-brand:focus-visible { outline:1px solid var(--signal); outline-offset:4px; }.live-brand b { color:var(--signal); font:500 var(--control-font-size) 'DM Mono'; margin-left:auto; }.live-brand-mark { width:19px;height:19px;flex:0 0 auto; }.workspace-rail :deep(.rail-toggle){background:#090d0c;color:var(--signal);border-color:rgba(159,255,216,.28)}.workspace-rail :deep(.rail-toggle:hover){background:var(--signal);color:#07100d}
.rail-label { display:flex; align-items:center; justify-content:space-between; color:#53605a; font:8px 'DM Mono'; letter-spacing:.12em; text-transform:uppercase; padding:3px 3px 0; }.rail-label button { border:0; background:transparent; color:#71817a; font-size:var(--control-font-size); }.rail-label button:hover { color:var(--signal); }
.role-switcher-wrap { position:relative; }.role-switcher { width:100%; display:grid; grid-template-columns:42px 1fr auto; gap:11px; align-items:center; padding:10px; text-align:left; color:var(--mist); border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.035); }.mini-avatar,.user-avatar { width:42px; height:42px; border-radius:50%; overflow:hidden; display:grid; place-items:center; background:#163227; color:var(--signal); font:600 var(--control-font-size) Syne; }.mini-avatar img,.user-avatar img { width:100%; height:100%; object-fit:cover; }.mini-avatar i,.user-avatar i { font-style:normal; }.role-switcher > span:nth-child(2) { min-width:0; }.role-switcher strong,.role-switcher small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.role-switcher strong { font:600 13px Syne; }.role-switcher small { color:#69756f; font:var(--control-font-size) 'DM Mono'; margin-top:5px; }.role-switcher > b { color:#52605a; }
.role-menu { position:absolute; z-index:10; inset:calc(100% + 7px) 0 auto; padding:5px; border:1px solid rgba(159,255,216,.18); background:#101614; box-shadow:0 24px 50px rgba(0,0,0,.5); }.role-menu button { width:100%; min-height:40px; border:0; display:grid; grid-template-columns:29px 1fr auto; align-items:center; gap:9px; text-align:left; color:#93a19a; background:transparent; }.role-menu button:hover,.role-menu button.active { background:rgba(159,255,216,.07); color:var(--mist); }.role-menu button > span { width:27px;height:27px;border-radius:50%;display:grid;place-items:center;background:#17241f;color:var(--signal);font:var(--control-font-size) Syne; }.role-menu strong { font-size:var(--control-font-size); }.role-menu i { color:var(--signal); font-size:var(--control-font-size); }.role-menu .new-role { border-top:1px solid rgba(255,255,255,.07); margin-top:4px; padding-top:4px; }
.new-conversation { min-height:45px; display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:9px; padding:0 12px; border:1px solid rgba(159,255,216,.22); background:rgba(159,255,216,.07); color:var(--mist); text-align:left; }.new-conversation > span { color:var(--signal); font-size:18px; }.new-conversation strong { font-size:var(--control-font-size); }.new-conversation small { color:#577068; font:var(--control-font-size) 'DM Mono'; }
.conversation-label { margin-top:2px; }.conversation-list { min-height:0; overflow:auto; scrollbar-width:thin; scrollbar-color:#31443d transparent; margin:0 -5px; padding:0 5px; }.conversation-list article { position:relative; display:grid; grid-template-columns:1fr auto; margin:2px 0; border-left:2px solid transparent; }.conversation-list article.active { border-left-color:var(--signal); background:rgba(159,255,216,.055); }.conversation-main { min-width:0; border:0; background:transparent; color:#75817c; display:grid; grid-template-columns:8px 1fr; align-items:center; gap:7px; padding:10px 6px 10px 9px; text-align:left; }.conversation-main > i { width:4px;height:4px;border-radius:50%;background:#3d4944; }.active .conversation-main > i { background:var(--signal);box-shadow:0 0 8px var(--signal); }.conversation-main > span { min-width:0; }.conversation-main strong,.conversation-main small { display:block; }.conversation-main strong { overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--control-font-size);font-weight:500; }.conversation-main small { margin-top:4px;color:#414b47;font:var(--control-font-size) 'DM Mono'; }.conversation-main input { width:100%;border:0;border-bottom:1px solid var(--signal);outline:0;background:transparent;color:var(--mist);font-size:var(--control-font-size); }.conversation-actions { display:flex;align-items:center;opacity:0;transition:opacity .16s; }.conversation-list article:hover .conversation-actions { opacity:1; }.conversation-actions button { width:22px;height:28px;border:0;background:transparent;color:#63706a; }.conversation-actions button:hover { color:var(--signal); }
.rail-loading,.empty-conversations { color:#48534e;font:8px/1.7 'DM Mono';text-align:center;padding:26px 5px; }.rail-loading i { display:inline-block;width:8px;height:8px;border:1px solid #43554d;border-top-color:var(--signal);border-radius:50%;animation:spin .8s linear infinite;margin-right:7px; }.empty-conversations span { color:#33403a; }
.rail-profile { margin-top:auto; display:grid;grid-template-columns:36px 1fr auto;align-items:center;gap:9px;padding:10px 4px 0;border-top:1px solid rgba(255,255,255,.07); }.rail-profile .user-avatar { width:34px;height:34px;border-radius:5px; }.rail-profile > span:nth-child(2) { min-width:0; }.rail-profile strong,.rail-profile small { display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }.rail-profile strong { font-size:10px; }.rail-profile small { color:#53605a;font:7px 'DM Mono';margin-top:3px; }.rail-profile button { width:28px;height:28px;border:1px solid rgba(255,255,255,.08);background:#0c1210;color:#5e6c66; }
.live-console { min-width:0;min-height:0;display:grid;grid-template-rows:86px minmax(0,1fr) 104px;position:relative;background-image:linear-gradient(rgba(159,255,216,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(159,255,216,.03) 1px,transparent 1px);background-size:44px 44px; }.live-console::before { content:'';position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 38% 44%,rgba(48,160,125,.11),transparent 34%); }
.console-head { z-index:1;display:flex;justify-content:space-between;align-items:center;padding:18px 28px;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(7,10,9,.78);backdrop-filter:blur(14px); }.eyebrow { display:block;color:#53605a;font:8px 'DM Mono';letter-spacing:.13em;margin-bottom:5px;max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }.console-head h1 { margin:0;font:600 24px/1 Syne;letter-spacing:-.035em; }.console-head h1 em { color:var(--signal);font-style:normal;font-weight:500; }.head-metrics { display:flex;align-items:center;gap:9px; }.head-metrics > span,.head-metrics button { height:31px;display:inline-flex;align-items:center;gap:7px;padding:0 10px;border:1px solid rgba(255,255,255,.1);background:#0b0f0e;color:#7c8983;font:var(--control-font-size) 'DM Mono';letter-spacing:.07em; }.head-metrics span i { width:5px;height:5px;border-radius:50%;background:#414b46; }.live-shell:not([data-phase='idle']) .head-metrics span i { background:var(--signal);box-shadow:0 0 9px var(--signal); }.head-metrics .tier { color:var(--signal); }.head-metrics button b { color:#45504b; }
.console-body { z-index:1;min-height:0;display:grid;grid-template-columns:minmax(420px,1fr) minmax(330px,39%); }.voice-stage { min-height:0;position:relative;display:grid;place-items:center;border-right:1px solid rgba(255,255,255,.08);overflow:hidden; }.stage-coordinates { position:absolute;inset:17px 21px auto;display:flex;justify-content:space-between;color:#38443f;font:8px 'DM Mono';letter-spacing:.12em; }.stage-status { position:absolute;left:50%;bottom:18px;transform:translateX(-50%);min-width:215px;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:9px;padding:9px 11px;border:1px solid rgba(255,255,255,.09);background:rgba(8,13,11,.8);backdrop-filter:blur(10px); }.status-pulse { width:7px;height:7px;border-radius:50%;background:#4d5753; }.live-shell:not([data-phase='idle']) .status-pulse { background:var(--signal);box-shadow:0 0 12px var(--signal);animation:pulse 1.3s ease infinite; }.stage-status small,.stage-status strong { display:block; }.stage-status small { color:#4e5c56;font:6px 'DM Mono';letter-spacing:.12em; }.stage-status strong { margin-top:2px;font-size:10px; }.stage-status code { color:#5e6b65;font:7px 'DM Mono'; }.live-error { position:absolute;bottom:68px;max-width:80%;padding:8px 10px;border:1px solid rgba(255,118,104,.25);background:rgba(255,118,104,.08);color:#ff9a90;font-size:9px; }
.transcript-panel { min-height:0;display:grid;grid-template-rows:61px minmax(0,1fr);background:rgba(8,11,10,.66); }.transcript-panel > header { display:flex;justify-content:space-between;align-items:center;padding:0 19px;border-bottom:1px solid rgba(255,255,255,.07); }.transcript-panel header span,.transcript-panel header strong { display:block; }.transcript-panel header span { color:#4d5a54;font:7px 'DM Mono';letter-spacing:.12em; }.transcript-panel header strong { margin-top:4px;font-size:11px; }.transcript-panel header > small { color:#44514b;font:7px 'DM Mono'; }.transcript-list { min-height:0;overflow-y:auto;padding:18px 19px 32px;scrollbar-width:thin;scrollbar-color:#2f443b transparent; }.transcript-empty { min-height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;color:#47534d; }.transcript-empty i { width:38px;height:38px;border:1px solid #33413b;border-radius:50%;margin-bottom:17px;position:relative; }.transcript-empty i::after { content:'';position:absolute;inset:13px;border-radius:50%;background:#30493f; }.transcript-empty span { font:8px 'DM Mono';letter-spacing:.15em; }.transcript-empty p { max-width:230px;color:#3f4945;font-size:10px;line-height:1.7; }.transcript-list article { margin-bottom:22px; }.speaker-line { display:flex;justify-content:space-between;align-items:center;margin-bottom:6px; }.speaker-line span { color:#76827c;font:8px 'DM Mono';letter-spacing:.08em; }.speaker-line code { color:#42504a;font:7px 'DM Mono'; }.transcript-list article p { margin:0;padding:12px 13px;color:#c5d1cb;background:rgba(255,255,255,.035);border-left:2px solid #3c4943;font-size:12px;line-height:1.7; }.transcript-list article.assistant p { border-left-color:var(--signal);background:rgba(159,255,216,.055); }.transcript-list article.user p { color:#9eaaa4; }.transcript-list article.interrupted p { opacity:.58;border-left-color:var(--danger); }.transcript-list article > small { display:block;margin-top:5px;color:var(--danger);font:7px 'DM Mono'; }.stash { opacity:.38; }.transcript-list article p > i { display:inline-block;width:5px;height:12px;margin-left:3px;background:var(--signal);animation:blink .7s steps(1) infinite;vertical-align:-2px; }
.call-dock { z-index:2;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:12px 25px;border-top:1px solid rgba(255,255,255,.08);background:#090d0c; }.dock-meta span,.dock-meta strong { display:block; }.dock-meta span { color:#3e4944;font:7px 'DM Mono';letter-spacing:.13em; }.dock-meta strong { margin-top:5px;color:#69756f;font-size:9px;font-weight:500; }.dock-meta.right { text-align:right; }.call-controls { display:flex;align-items:center;gap:13px; }.round-control { width:53px;height:53px;border-radius:50%;border:1px solid rgba(255,255,255,.12);background:#0e1412;color:#6e7b75;display:grid;place-items:center;gap:0;padding:8px; }.round-control svg { width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.5; }.round-control span { font-size:var(--control-font-size); }.round-control.active { color:var(--danger);border-color:rgba(255,118,104,.35); }.call-button { min-width:165px;height:67px;border:1px solid rgba(159,255,216,.28);background:rgba(159,255,216,.07);color:var(--mist);display:grid;grid-template-columns:38px 1fr;grid-template-rows:1fr 1fr;align-items:center;text-align:left;padding:8px 15px; }.call-icon { grid-row:1/3;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:var(--signal); }.call-icon i { width:8px;height:8px;border-radius:50%;background:#0a1612; }.call-button strong { align-self:end;font-size:var(--control-font-size); }.call-button small { align-self:start;color:#598071;font:var(--control-font-size) 'DM Mono';margin-top:2px; }.call-button.active { border-color:rgba(255,118,104,.35);background:rgba(255,118,104,.08); }.call-button.active .call-icon { background:var(--danger); }.call-button.active .call-icon i { border-radius:1px; }
.deck-backdrop { position:fixed;z-index:30;inset:0;background:rgba(0,0,0,.58);backdrop-filter:blur(7px);display:flex;justify-content:flex-end; }.settings-deck { width:min(600px,100%);height:100%;display:grid;grid-template-rows:auto auto minmax(0,1fr);background:#0d1210;border-left:1px solid rgba(159,255,216,.2);box-shadow:-32px 0 80px rgba(0,0,0,.46); }.deck-head { display:flex;justify-content:space-between;align-items:center;padding:25px 28px 20px; }.deck-head span { color:var(--signal);font:7px 'DM Mono';letter-spacing:.15em; }.deck-head h2 { margin:6px 0 0;font:600 23px Syne; }.deck-head > button { width:34px;height:34px;border:1px solid rgba(255,255,255,.1);background:transparent;color:#77837d;font-size:19px; }.deck-tabs { display:grid;grid-template-columns:repeat(3,1fr);padding:0 28px;border-bottom:1px solid rgba(255,255,255,.08); }.deck-tabs button { height:43px;border:0;border-bottom:2px solid transparent;background:transparent;color:#5e6b65;font-size:var(--control-font-size); }.deck-tabs button.active { color:var(--signal);border-bottom-color:var(--signal); }.deck-scroll { min-height:0;overflow-y:auto;padding:24px 28px 42px;scrollbar-width:thin;scrollbar-color:#31443d transparent; }.deck-section { margin-bottom:26px; }.deck-section > label { display:flex;align-items:center;gap:8px;margin-bottom:12px;color:#aeb9b4;font-size:10px;font-weight:600; }.deck-section > label > span { color:var(--signal);font:8px 'DM Mono'; }.deck-section > label b { margin-left:auto;color:#607069;font:8px 'DM Mono';font-weight:400; }.model-options { display:grid;grid-template-columns:1fr 1fr;gap:8px; }.model-options button { min-height:68px;display:grid;grid-template-columns:1fr auto;grid-template-rows:1fr 1fr;text-align:left;padding:12px 13px;border:1px solid rgba(255,255,255,.1);background:#101614;color:#75827c; }.model-options button strong { color:#c3cec8;font:600 14px Syne; }.model-options button small { align-self:end;font-size:var(--control-font-size); }.model-options button i { grid-row:1/3;width:7px;height:7px;border:1px solid #4a5751;border-radius:50%;align-self:center; }.model-options button.active { border-color:rgba(159,255,216,.42);background:rgba(159,255,216,.055); }.model-options button.active i { background:var(--signal);border-color:var(--signal);box-shadow:0 0 9px var(--signal); }.range-section input[type='range'] { width:100%;accent-color:var(--signal); }.range-axis { display:flex;justify-content:space-between;color:#48564f;font:7px 'DM Mono';margin-top:7px; }.range-section > p { color:#57645e;font-size:9px;line-height:1.6;margin:12px 0 0; }.primary-action { min-height:43px;padding:0 19px;border:1px solid var(--signal);background:var(--signal);color:#08110e;font-size:var(--control-font-size);font-weight:700; }.deck-scroll > .primary-action { width:100%; }.role-roster { display:flex;gap:8px;overflow-x:auto;margin-bottom:25px;padding-bottom:7px; }.role-roster button { flex:0 0 82px;border:1px solid rgba(255,255,255,.09);background:#101614;color:#77847e;padding:9px 6px; }.role-roster button > span { width:34px;height:34px;margin:0 auto 7px;border-radius:50%;overflow:hidden;display:grid;place-items:center;background:#17241f;color:var(--signal);font:var(--control-font-size) Syne; }.role-roster img { width:100%;height:100%;object-fit:cover; }.role-roster i { font-style:normal; }.role-roster strong { display:block;overflow:hidden;text-overflow:ellipsis;font-size:var(--control-font-size);white-space:nowrap; }.role-roster button.active { border-color:rgba(159,255,216,.4);color:var(--mist); }.role-roster .add-role span { font-size:17px; }.avatar-editor { display:grid;grid-template-columns:82px 1fr;gap:15px;align-items:center;margin-bottom:13px; }.avatar-preview { width:82px;height:82px;border-radius:50%;overflow:hidden;position:relative;border:1px solid rgba(159,255,216,.35);background:#17241f;color:var(--signal); }.avatar-preview img { width:100%;height:100%;object-fit:cover; }.avatar-preview > i { font:600 20px Syne;font-style:normal; }.avatar-preview small { position:absolute;inset:auto 0 0;padding:5px;background:rgba(0,0,0,.65);font-size:7px; }.avatar-editor div > span { font-size:10px;font-weight:600; }.avatar-editor p { color:#5f6d66;font-size:9px;line-height:1.5; }.avatar-editor div button { border:0;background:transparent;color:var(--danger);font-size:8px;padding:0; }.text-input { width:100%;height:42px;padding:0 12px;border:1px solid rgba(255,255,255,.11);outline:0;background:#0a0f0d;color:var(--mist);font-size:10px; }.text-input:focus { border-color:rgba(159,255,216,.45); }.voice-options { display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:9px; }.voice-options button { min-height:53px;border:1px solid rgba(255,255,255,.1);background:#101614;color:#75827c; }.voice-options strong,.voice-options small { display:block; }.voice-options strong { color:#bbc7c1;font-size:var(--control-font-size); }.voice-options small { margin-top:4px;font:var(--control-font-size) 'DM Mono'; }.voice-options button.active { border-color:rgba(159,255,216,.42);background:rgba(159,255,216,.055); }.prompt-section textarea { width:100%;min-height:148px;resize:vertical;padding:13px;border:1px solid rgba(255,255,255,.11);outline:0;background:#090e0c;color:#c7d2cc;font:10px/1.7 Manrope; }.prompt-section textarea:focus { border-color:rgba(159,255,216,.42); }.prompt-section > small { color:#53615a;font-size:8px; }.memory-switch-row { display:grid;grid-template-columns:1fr auto;align-items:center;gap:15px;padding:14px;border:1px solid rgba(255,255,255,.09);background:#101614;margin-bottom:22px; }.memory-switch-row strong,.memory-switch-row small { display:block; }.memory-switch-row strong { font-size:10px; }.memory-switch-row small { color:#58655f;font-size:8px;line-height:1.5;margin-top:5px; }.memory-switch-row > button { width:42px;height:23px;border:0;border-radius:20px;background:#27302c;padding:3px; }.memory-switch-row button i { display:block;width:17px;height:17px;border-radius:50%;background:#6c7772;transition:transform .2s; }.memory-switch-row button.active { background:rgba(159,255,216,.25); }.memory-switch-row button.active i { background:var(--signal);transform:translateX(19px); }.role-actions,.memory-actions { display:flex;justify-content:flex-end;gap:8px; }.danger-action,.memory-actions > button { min-height:43px;padding:0 16px;border:1px solid rgba(255,255,255,.1);background:transparent;color:#77837d;font-size:var(--control-font-size); }.danger-action { color:var(--danger);border-color:rgba(255,118,104,.22);margin-right:auto; }.memory-hero { display:grid;grid-template-columns:58px 1fr;gap:15px;align-items:center;padding:17px;border:1px solid rgba(159,255,216,.15);background:rgba(159,255,216,.04);margin-bottom:25px; }.memory-hero > span { width:54px;height:54px;border-radius:50%;display:grid;place-items:center;background:#183127;color:var(--signal);font:600 12px Syne; }.memory-hero small { color:var(--signal);font:7px 'DM Mono';letter-spacing:.12em; }.memory-hero h3 { margin:4px 0;font:600 15px Syne; }.memory-hero p { margin:0;color:#5e6b65;font-size:8px;line-height:1.5; }.memory-editor textarea { min-height:300px; }.memory-actions .primary-action { margin-left:auto; }.memory-note { color:#4e5a54;font-size:8px;line-height:1.6;margin-top:17px; }
.deck-enter-active,.deck-leave-active { transition:opacity .2s; }.deck-enter-active .settings-deck,.deck-leave-active .settings-deck { transition:transform .28s cubic-bezier(.2,.8,.2,1); }.deck-enter-from,.deck-leave-to { opacity:0; }.deck-enter-from .settings-deck,.deck-leave-to .settings-deck { transform:translateX(60px); }.pop-enter-active,.pop-leave-active { transition:opacity .15s,transform .15s; }.pop-enter-from,.pop-leave-to { opacity:0;transform:translateY(-5px); }
@keyframes spin { to { transform:rotate(360deg); } } @keyframes pulse { 50% { opacity:.35; } } @keyframes blink { 50% { opacity:0; } }
@media (min-width:821px) { .live-shell.rail-collapsed { grid-template-columns:72px minmax(0,1fr); }.rail-collapsed .workspace-rail{padding-inline:10px}.rail-collapsed .live-brand{justify-content:center;padding-inline:0}.rail-collapsed .live-brand>span,.rail-collapsed .live-brand>b,.rail-collapsed .rail-label,.rail-collapsed .role-switcher-wrap,.rail-collapsed .conversation-list,.rail-collapsed .rail-profile{display:none}.rail-collapsed .new-conversation{display:grid;grid-template:1fr/1fr;place-items:center;padding:0;min-height:45px}.rail-collapsed .new-conversation>span{font-size:22px}.rail-collapsed .new-conversation>strong,.rail-collapsed .new-conversation>small{display:none} }
@media (max-width:1050px) { .live-shell { grid-template-columns:250px minmax(0,1fr); }.console-body { grid-template-columns:1fr 340px; }.dock-meta { display:none; }.call-dock { grid-template-columns:1fr;justify-items:center; } }
@media (max-width:820px) { .live-shell { grid-template-columns:1fr;height:auto;min-height:100dvh;overflow:auto; }.workspace-rail { min-height:auto; }.conversation-list { max-height:230px; }.live-console { min-height:900px; }.console-body { grid-template-columns:1fr;grid-template-rows:430px 430px; }.voice-stage { border-right:0;border-bottom:1px solid rgba(255,255,255,.08); }.head-metrics > span:not(.tier) { display:none; } }
.custom-voice-editor{display:grid;gap:8px;margin-top:10px;padding:12px;border:1px solid rgba(159,255,216,.12);background:rgba(159,255,216,.025)}.custom-voice-editor>label{color:#66756e;font:8px 'DM Mono';letter-spacing:.08em}.custom-voice-editor select{width:100%;height:42px;padding:0 11px;border:1px solid rgba(255,255,255,.11);outline:0;background:#090e0c;color:#c3cec8;font-size:9px}.custom-voice-editor select:focus{border-color:rgba(159,255,216,.45)}.custom-voice-editor>p{margin:0;color:#52615a;font:8px/1.55 'DM Mono'}.custom-voice-editor>p.voice-binding-error{padding:8px;border-left:2px solid var(--danger);background:rgba(255,118,104,.06);color:#e68d83}.call-dock{position:relative}.dock-voice-warning{position:absolute;left:50%;bottom:3px;transform:translateX(-50%);margin:0;color:#e68d83;font:7px 'DM Mono';white-space:nowrap}
</style>
