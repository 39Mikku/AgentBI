<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import * as api from '@/api/playground'
import * as ttsApi from '@/api/toolbox-tts'
import { listProviders } from '@/api/providers'
import type { ProviderProfile } from '@/api/chat-types'
import type { TtsCapabilities, TtsCustomVoice } from '@/api/toolbox-tts-types'
import type {
  PlaygroundContextEntry,
  PlaygroundPersona,
  PlaygroundPreferences,
  PlaygroundProfile,
  PlaygroundProfileSettings,
  PlaygroundProfileType,
  PlaygroundPromptModule,
  PlaygroundPromptSlot,
  PlaygroundStateTemplates,
} from '@/api/playground-types'
import PlaygroundAssetPicker from './PlaygroundAssetPicker.vue'
import PlaygroundLorebookEditor from './PlaygroundLorebookEditor.vue'
import PlaygroundPromptEditor from './PlaygroundPromptEditor.vue'
import PlaygroundStateEditor from './PlaygroundStateEditor.vue'


const props = defineProps<{
  profile: PlaygroundProfile | null
  userId: string
  initialType: PlaygroundProfileType
  preferences: PlaygroundPreferences
  templates: PlaygroundStateTemplates | null
}>()
const emit = defineEmits<{
  saved: [profile: PlaygroundProfile]
  deleted: [profileId: string]
}>()

const providers = ref<ProviderProfile[]>([])
const ttsCapabilities = ref<TtsCapabilities>({ providers: [] })
const ttsVoices = ref<TtsCustomVoice[]>([])
const saving = ref(false)
const state = ref<'idle' | 'saved' | 'error'>('idle')
const error = ref('')
const form = ref(baseForm(props.initialType))
const persona = ref<PlaygroundPersona>(basePersona())
const modules = ref<PlaygroundPromptModule[]>([])
const entries = ref<PlaygroundContextEntry[]>([])
const summaryProvider = computed(() =>
  providers.value.find((item) => item.id === form.value.settings.summary.provider_id),
)
const ttsProvider = computed(() =>
  ttsCapabilities.value.providers.find((item) => item.id === form.value.settings.tts.provider),
)
const ttsVoiceOptions = computed(() => {
  const provider = ttsProvider.value
  if (!provider) return []
  const values = new Map<string, string>()
  for (const voice of provider.builtin_voices) values.set(voice.id, voice.name)
  for (const voice of ttsVoices.value) {
    if (voice.provider !== provider.id) continue
    if (voice.bound_model && voice.bound_model !== form.value.settings.tts.model) continue
    values.set(voice.external_voice_id, `${voice.display_name} · 已登记`)
  }
  return [...values].map(([value, label]) => ({ value, label }))
})

function settings(): PlaygroundProfileSettings {
  return {
    summary: {
      enabled: false,
      trigger_new_message_count: null,
      retain_recent_message_count: null,
      provider_id: null,
      model: null,
      injection_position: 'system_end',
    },
    state: {
      enabled: false,
      template: 'custom',
      variables: [],
      update_instructions: '',
      injection_position: 'system_end',
    },
    action_options: { enabled: false, style_prompt: '' },
    tts: {
      enabled: false,
      auto_play: false,
      provider: null,
      model: null,
      voice_id: null,
      audio_format: 'mp3',
      parameters: {},
    },
  }
}

function baseForm(profileType: PlaygroundProfileType) {
  return {
    profile_type: profileType,
    name: '',
    avatar_attachment_id: null as string | null,
    background_attachment_id: null as string | null,
    main_prompt: '',
    opening_message: '',
    settings: settings(),
  }
}

function basePersona(): PlaygroundPersona {
  return {
    name: '', avatar_attachment_id: null, identity_text: '', background: '',
    personality: '', initial_relationship: '', enabled: true,
    injection_position: 'system_end',
  }
}

async function loadResources(profile: PlaygroundProfile | null) {
  state.value = 'idle'
  error.value = ''
  if (!profile) {
    form.value = baseForm(props.initialType)
    persona.value = basePersona()
    modules.value = []
    entries.value = []
    return
  }
  form.value = {
    profile_type: profile.profile_type,
    name: profile.name,
    avatar_attachment_id: profile.avatar_attachment_id || null,
    background_attachment_id: profile.background_attachment_id || null,
    main_prompt: profile.main_prompt,
    opening_message: profile.opening_message,
    settings: JSON.parse(JSON.stringify(profile.settings)) as PlaygroundProfileSettings,
  }
  const [storedPersona, storedModules, storedEntries] = await Promise.all([
    api.getPlaygroundPersona(profile.id, props.userId),
    api.listPlaygroundPromptModules(profile.id, props.userId),
    api.listPlaygroundContextEntries(profile.id, props.userId),
  ])
  if (props.profile?.id !== profile.id) return
  persona.value = storedPersona || basePersona()
  modules.value = storedModules
  entries.value = storedEntries
}

function changeType(profileType: PlaygroundProfileType) {
  form.value.profile_type = profileType
  if (profileType === 'world') {
    form.value.settings.tts.enabled = false
    form.value.settings.tts.auto_play = false
  }
}

function selectTtsProvider() {
  const settings = form.value.settings.tts
  settings.model = ttsProvider.value?.models[0]?.id || null
  settings.voice_id = null
  const formats = ttsProvider.value?.audio_formats || []
  if (!formats.includes(settings.audio_format)) settings.audio_format = formats[0] || 'mp3'
}

function selectTtsModel() {
  form.value.settings.tts.voice_id = null
}

async function save() {
  if (!form.value.name.trim()) {
    error.value = '请填写角色或世界名称'
    state.value = 'error'
    return
  }
  saving.value = true
  state.value = 'idle'
  error.value = ''
  try {
    const profileFields = {
      profile_type: form.value.profile_type,
      name: form.value.name.trim(),
      avatar_attachment_id: form.value.avatar_attachment_id,
      background_attachment_id: form.value.background_attachment_id,
      main_prompt: form.value.main_prompt,
      opening_message: form.value.opening_message,
      settings: form.value.settings,
    }
    const saved = props.profile
      ? await api.updatePlaygroundProfile(props.profile.id, props.userId, profileFields)
      : await api.createPlaygroundProfile({ user_id: props.userId, ...profileFields })
    await Promise.all([
      api.savePlaygroundPersona(saved.id, props.userId, persona.value),
      api.savePlaygroundPromptModules(saved.id, props.userId, modules.value),
      api.savePlaygroundContextEntries(saved.id, props.userId, entries.value),
    ])
    state.value = 'saved'
    emit('saved', saved)
  } catch (reason) {
    state.value = 'error'
    error.value = reason instanceof Error ? reason.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.profile) return
  const confirmed = window.confirm(
    `确认删除「${props.profile.name}」？\n\n它拥有的所有 Playground 会话、世界书、人设与会话总结都会被删除；共享附件文件不会自动删除。`,
  )
  if (!confirmed) return
  saving.value = true
  try {
    await api.deletePlaygroundProfile(props.profile.id, props.userId)
    emit('deleted', props.profile.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '删除失败'
    state.value = 'error'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.profile,
  (profile) => void loadResources(profile),
  { immediate: true },
)
watch(
  () => props.initialType,
  (value) => {
    if (!props.profile) changeType(value)
  },
)
onMounted(async () => {
  const [modelProviders, capabilities, voices] = await Promise.allSettled([
    listProviders(),
    ttsApi.listTtsCapabilities(),
    ttsApi.listTtsVoices(props.userId),
  ])
  if (modelProviders.status === 'fulfilled') providers.value = modelProviders.value
  if (capabilities.status === 'fulfilled') ttsCapabilities.value = capabilities.value
  if (voices.status === 'fulfilled') ttsVoices.value = voices.value
})
</script>

<template>
  <form class="profile-editor" @submit.prevent="save">
    <section class="basic editor-section">
      <header class="profile-heading"><div><span>01 / IDENTITY</span><h2>{{ profile ? form.name || '未命名资料' : '创建新资料' }}</h2><p>{{ form.profile_type === 'character' ? '单角色对话，支持头像、背景与临时 TTS。' : '广阔世界叙事，不解析发言人，也不启用 TTS。' }}</p></div><div class="type-switch"><button type="button" :class="{ active: form.profile_type === 'character' }" @click="changeType('character')">角色</button><button type="button" :class="{ active: form.profile_type === 'world' }" @click="changeType('world')">世界</button></div></header>
      <div class="basic-grid">
        <label class="wide"><span>名称</span><input v-model="form.name" maxlength="100" placeholder="例如：雷电芽衣 / 提瓦特大陆" /></label>
        <PlaygroundAssetPicker v-model="form.avatar_attachment_id" :user-id="userId" kind="avatar" :provider-id="preferences.providerId" />
        <PlaygroundAssetPicker v-model="form.background_attachment_id" :user-id="userId" kind="background" :provider-id="preferences.providerId" />
        <label class="wide"><span>主提示词</span><textarea v-model="form.main_prompt" rows="9" placeholder="定义角色身份、语言风格、行为边界，或整个世界的运行规则…"></textarea></label>
        <label class="wide"><span>开场消息</span><textarea v-model="form.opening_message" rows="5" placeholder="它会作为每个新会话的第一条正式角色 / 世界消息，可在会话内另行编辑版本。"></textarea></label>
      </div>
    </section>

    <PlaygroundPromptEditor v-model:persona="persona" v-model:modules="modules" />
    <PlaygroundLorebookEditor v-model="entries" />

    <section class="summary editor-section">
      <header><div><span>05 / LONG CONTEXT</span><h3>长会话大总结</h3><p>每个会话只维护一份精炼记录，并在消息时间线上标记总结位置。</p></div><label class="switch"><input v-model="form.settings.summary.enabled" type="checkbox" /><i></i><b>{{ form.settings.summary.enabled ? '启用' : '停用' }}</b></label></header>
      <div class="summary-grid" :class="{ disabled: !form.settings.summary.enabled }">
        <label><span>触发新消息数</span><input v-model.number="form.settings.summary.trigger_new_message_count" type="number" min="4" max="500" :placeholder="String(preferences.summaryTriggerMessages)" /></label>
        <label><span>保留最近消息数</span><input v-model.number="form.settings.summary.retain_recent_message_count" type="number" min="2" max="100" :placeholder="String(preferences.summaryRetainMessages)" /></label>
        <label><span>覆盖提供商</span><select v-model="form.settings.summary.provider_id"><option :value="null">跟随公共设置</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option></select></label>
        <label><span>覆盖模型</span><select v-model="form.settings.summary.model"><option :value="null">跟随公共设置</option><option v-for="model in summaryProvider?.available_models || []" :key="model" :value="model">{{ model }}</option></select></label>
        <label class="wide"><span>注入位置</span><select v-model="form.settings.summary.injection_position"><option value="system_start">系统提示词开头</option><option value="system_end">系统提示词末尾</option><option value="after_last_assistant">上一条回复后</option><option value="before_latest_user">最新用户输入前</option><option value="after_latest_user">最新用户输入后</option></select></label>
      </div>
    </section>

    <PlaygroundStateEditor v-model="form.settings.state" :templates="templates" />

    <section class="options editor-section">
      <header><div><span>07 / ACTION OPTIONS</span><h3>行动选项</h3><p>每轮生成四个不同风格的推进选项；点击后作为真实用户消息发送。</p></div><label class="switch"><input v-model="form.settings.action_options.enabled" type="checkbox" /><i></i><b>{{ form.settings.action_options.enabled ? '启用' : '停用' }}</b></label></header>
      <label :class="{ disabled: !form.settings.action_options.enabled }"><span>选项风格要求</span><textarea v-model="form.settings.action_options.style_prompt" rows="4" placeholder="例如：分别提供温和、冒险、试探和意外的选择。固定 JSON 格式与四选项数量不会被覆盖。"></textarea></label>
    </section>

    <section v-if="form.profile_type === 'character'" class="tts editor-section">
      <header><div><span>08 / VOICE</span><h3>临时朗读</h3><p>复用语音工作台的供应商与音色。关闭自动朗读后，也可在消息上手动播放。</p></div><label class="switch"><input v-model="form.settings.tts.enabled" type="checkbox" /><i></i><b>{{ form.settings.tts.enabled ? '启用' : '停用' }}</b></label></header>
      <div class="tts-grid" :class="{ disabled: !form.settings.tts.enabled }">
        <label><span>供应商</span><select v-model="form.settings.tts.provider" @change="selectTtsProvider"><option :value="null">选择供应商</option><option v-for="provider in ttsCapabilities.providers" :key="provider.id" :value="provider.id">{{ provider.label }}{{ provider.configured ? '' : ' · 未配置' }}</option></select></label>
        <label><span>模型</span><select v-model="form.settings.tts.model" @change="selectTtsModel"><option :value="null">选择模型</option><option v-if="form.settings.tts.model && !ttsProvider?.models.some((item) => item.id === form.settings.tts.model)" :value="form.settings.tts.model">{{ form.settings.tts.model }}</option><option v-for="model in ttsProvider?.models || []" :key="model.id" :value="model.id">{{ model.label }}</option></select></label>
        <label><span>音色</span><select v-model="form.settings.tts.voice_id"><option :value="null">选择预置或已登记音色</option><option v-if="form.settings.tts.voice_id && !ttsVoiceOptions.some((item) => item.value === form.settings.tts.voice_id)" :value="form.settings.tts.voice_id">{{ form.settings.tts.voice_id }}</option><option v-for="voice in ttsVoiceOptions" :key="voice.value" :value="voice.value">{{ voice.label }}</option></select></label>
        <label><span>格式</span><select v-model="form.settings.tts.audio_format"><option v-for="format in ttsProvider?.audio_formats.filter((item) => item !== 'pcm') || ['mp3', 'wav']" :key="format" :value="format">{{ format.toUpperCase() }}</option></select></label>
        <label class="auto"><input v-model="form.settings.tts.auto_play" type="checkbox" /><span>回复完成后自动生成并播放</span></label>
      </div>
    </section>

    <footer class="save-dock">
      <div><span v-if="state === 'saved'">已保存，新的会话将使用最新资料。</span><span v-else-if="state === 'error'" class="save-error">{{ error }}</span><span v-else>资料变更不会回写已有会话的开场消息。</span></div>
      <button v-if="profile" type="button" class="delete" :disabled="saving" @click="remove">删除 {{ form.profile_type === 'character' ? '角色' : '世界' }}</button>
      <button type="submit" class="save" :disabled="saving">{{ saving ? '保存中…' : profile ? '保存全部设置' : '创建并保存' }} <b>↗</b></button>
    </footer>
  </form>
</template>

<style scoped>
.profile-editor{--pg-acid:#d7ff3f;--pg-paper:#e8ece7;--pg-muted:#747d76;--pg-line:#343a36;display:block;color:var(--pg-paper);font-family:var(--font-sans)}.editor-section{display:grid;gap:20px;padding:27px}.profile-heading,.summary>header,.options>header,.tts>header{display:flex;justify-content:space-between;align-items:start;gap:20px}.profile-heading span,.summary header span,.options header span,.tts header span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.14em}.profile-heading h2{margin:9px 0 6px;font:600 28px/1 var(--font-display);letter-spacing:-.055em}.profile-heading p,.summary header p,.options header p,.tts header p{margin:0;color:var(--pg-muted);font-size:9px}.type-switch{display:flex;padding:3px;border:1px solid var(--pg-line);background:#111411}.type-switch button{min-width:65px;border:0;background:none;color:var(--pg-muted);padding:9px;font:8px var(--font-mono);cursor:pointer}.type-switch button.active{background:var(--pg-acid);color:#11130f}.basic-grid{display:grid;grid-template-columns:1fr 1.35fr;gap:18px}.basic-grid>.wide{grid-column:1/-1}.basic-grid>label,.summary-grid label,.options>label,.tts-grid label{display:grid;gap:7px}.basic-grid label>span,.summary-grid label>span,.options>label>span,.tts-grid label>span{color:var(--pg-muted);font:7px var(--font-mono)}input,select,textarea{box-sizing:border-box;width:100%;border:1px solid var(--pg-line);outline:0;background:#0f1210;color:var(--pg-paper);padding:10px;font:9px/1.6 var(--font-sans)}input,select{height:39px}select option{background:#151815}.summary,.options,.tts{border-top:1px solid var(--pg-line)}.summary h3,.options h3,.tts h3{margin:8px 0 5px;font-size:18px}.switch{display:flex;align-items:center;gap:8px;color:var(--pg-muted);font:7px var(--font-mono);cursor:pointer}.switch input{display:none}.switch i{position:relative;width:31px;height:16px;border:1px solid var(--pg-line);background:#101310}.switch i:after{content:'';position:absolute;width:8px;height:8px;left:3px;top:3px;background:#626963;transition:.2s}.switch input:checked+i{border-color:var(--pg-acid)}.switch input:checked+i:after{left:18px;background:var(--pg-acid)}.summary-grid,.tts-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.summary-grid .wide{grid-column:1/-1}.disabled{opacity:.35;pointer-events:none}.tts-grid .auto{display:flex;align-items:center;grid-column:1/-1}.tts-grid .auto input{width:auto;height:auto;accent-color:var(--pg-acid)}.save-dock{position:sticky;z-index:4;bottom:0;display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:10px;padding:14px 20px;border-top:1px solid #464e48;background:rgba(17,20,18,.96);backdrop-filter:blur(12px)}.save-dock span{color:var(--pg-muted);font:7px/1.5 var(--font-mono)}.save-dock .save-error{color:#ff8c79}.save-dock button{height:40px;padding:0 14px;font:8px var(--font-mono);cursor:pointer}.save-dock .delete{border:1px solid #714c45;background:none;color:#df8575}.save-dock .save{min-width:170px;border:1px solid var(--pg-acid);background:var(--pg-acid);color:#11130f;text-align:left;font-weight:700}.save-dock .save b{float:right;font-size:14px}.save-dock button:disabled{opacity:.4}@media(max-width:760px){.editor-section{padding:20px}.profile-heading,.summary>header,.options>header,.tts>header{flex-direction:column}.basic-grid,.summary-grid,.tts-grid{grid-template-columns:1fr}.basic-grid>.wide,.summary-grid .wide{grid-column:auto}.save-dock{grid-template-columns:1fr 1fr}.save-dock div{grid-column:1/-1}.save-dock .save{min-width:0}}
</style>
