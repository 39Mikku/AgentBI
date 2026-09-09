<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import * as ttsApi from '@/api/toolbox-tts'
import type {
  LiveVoiceTargetModel,
  TtsAudioFormat,
  TtsCapabilityProvider,
  TtsCustomVoice,
  TtsProviderId,
  TtsTrackConfig,
  TtsTrackResult,
  TtsVoiceInput,
} from '@/api/toolbox-tts-types'
import { useWorkspaceStore } from '@/stores/workspace'
import { applyGeneratedScript, availableVoices, generateTracks, releaseTrackResults } from '@/toolbox/voice-workbench'

const router = useRouter()
const workspace = useWorkspaceStore()
const userId = computed(() => workspace.userId)
const providers = ref<TtsCapabilityProvider[]>([])
const customVoices = ref<TtsCustomVoice[]>([])
const tracks = ref<TtsTrackConfig[]>([])
const results = ref<TtsTrackResult[]>([])
const text = ref('')
const scriptInstruction = ref('')
const scriptGenerating = ref(false)
const scriptError = ref('')
const scriptMeta = ref('')
const comparison = ref(false)
const loading = ref(true)
const loadError = ref('')
const generating = ref(false)
const voiceManagerOpen = ref(false)
const savingVoice = ref(false)
const voiceError = ref('')
const voiceSuccess = ref('')
const voiceManagerMode = ref<'register' | 'enroll-live'>('register')
let trackSequence = 0

const voiceForm = reactive<TtsVoiceInput>({
  user_id: '', provider: 'minimax', display_name: '', external_voice_id: '',
  voice_kind: 'cloned', bound_model: 'speech-2.8-hd', provider_metadata: {},
})

const liveEnrollmentForm = reactive({
  display_name: '',
  target_model: 'qwen-audio-3.0-realtime-plus' as LiveVoiceTargetModel,
  prefix: 'livevoice',
  audio_url: '',
})

const liveEnrollmentModels: Array<{ id: LiveVoiceTargetModel; label: string }> = [
  { id: 'qwen-audio-3.0-realtime-plus', label: 'Qwen Audio Realtime Plus' },
  { id: 'qwen-audio-3.0-realtime-flash', label: 'Qwen Audio Realtime Flash' },
]

const configuredCount = computed(() => providers.value.filter((provider) => provider.configured).length)
const clonedProviders = computed(() => providers.value.filter((provider) =>
  provider.models.some((model) => model.voice_kinds.includes('cloned')),
))
const voiceFormProvider = computed(() => providers.value.find((provider) => provider.id === voiceForm.provider))
const voiceFormModels = computed(() => voiceFormProvider.value?.models.filter((model) => model.voice_kinds.includes('cloned')) || [])
const successfulResults = computed(() => results.value.filter((result) => result.status === 'success').length)

function providerFor(track: TtsTrackConfig) {
  return providers.value.find((provider) => provider.id === track.provider)
}

function voicesFor(track: TtsTrackConfig) {
  const provider = providerFor(track)
  return provider ? availableVoices(provider, track.model, customVoices.value) : []
}

function defaultsFor(provider: TtsCapabilityProvider) {
  return Object.fromEntries(provider.parameters.map((parameter) => [parameter.key, parameter.default]))
}

function makeTrack(providerId?: TtsProviderId): TtsTrackConfig {
  const provider = providers.value.find((item) => item.id === providerId)
    || providers.value.find((item) => item.configured)
    || providers.value[0]
  if (!provider) throw new Error('没有可用的语音供应商')
  const model = provider.models[0]
  if (!model) throw new Error('供应商没有可用模型')
  const draft: TtsTrackConfig = {
    id: `track-${++trackSequence}`,
    provider: provider.id,
    model: model.id,
    voice_id: '',
    audio_format: provider.audio_formats[0] || 'mp3',
    parameters: defaultsFor(provider),
  }
  draft.voice_id = voicesFor(draft)[0]?.value || ''
  return draft
}

function chooseProvider(track: TtsTrackConfig, providerId: TtsProviderId) {
  const provider = providers.value.find((item) => item.id === providerId)
  const model = provider?.models[0]
  if (!provider || !model) return
  track.provider = provider.id
  track.model = model.id
  track.audio_format = provider.audio_formats[0] || 'mp3'
  track.parameters = defaultsFor(provider)
  track.voice_id = voicesFor(track)[0]?.value || ''
}

function chooseModel(track: TtsTrackConfig, modelId: string) {
  track.model = modelId
  track.voice_id = voicesFor(track)[0]?.value || ''
}

function updateParameter(track: TtsTrackConfig, key: string, value: string, numeric = false) {
  track.parameters[key] = numeric ? Number(value) : value
}

function toggleComparison() {
  comparison.value = !comparison.value
  if (comparison.value && tracks.value.length === 1) {
    const alternative = providers.value.find((provider) => provider.id !== tracks.value[0]?.provider && provider.configured)
    tracks.value.push(makeTrack(alternative?.id))
  }
  if (!comparison.value && tracks.value.length > 1) {
    const kept = tracks.value[0]
    tracks.value = kept ? [kept] : []
    releaseTrackResults(results.value.slice(1))
    results.value = results.value.filter((result) => result.trackId === kept?.id)
  }
}

function addTrack() {
  if (tracks.value.length < 4) tracks.value.push(makeTrack())
}

function removeTrack(trackId: string) {
  const result = results.value.find((item) => item.trackId === trackId)
  if (result) releaseTrackResults([result])
  results.value = results.value.filter((item) => item.trackId !== trackId)
  tracks.value = tracks.value.filter((track) => track.id !== trackId)
}

function resultFor(trackId: string) {
  return results.value.find((result) => result.trackId === trackId)
}

function replaceResult(result: TtsTrackResult) {
  const index = results.value.findIndex((item) => item.trackId === result.trackId)
  if (index >= 0) results.value[index] = result
  else results.value.push(result)
}

async function runSynthesis() {
  loadError.value = ''
  if (!text.value.trim()) { loadError.value = '先在右侧写下要合成的文本。'; return }
  const invalid = tracks.value.find((track) => !track.voice_id || !providerFor(track)?.configured)
  if (invalid) { loadError.value = '存在未配置供应商或尚未选择音色的轨道。'; return }
  const previous = results.value
  results.value = tracks.value.map((track) => ({ trackId: track.id, status: 'loading' }))
  generating.value = true
  try {
    results.value = await generateTracks(
      tracks.value,
      text.value.trim(),
      (track, content) => ttsApi.synthesizeTts({
        user_id: userId.value,
        provider: track.provider,
        model: track.model,
        voice_id: track.voice_id,
        text: content,
        audio_format: track.audio_format,
        parameters: track.parameters,
      }),
      URL,
      previous,
      replaceResult,
    )
  } finally {
    generating.value = false
  }
}

async function generateScript() {
  const instruction = scriptInstruction.value.trim()
  if (!instruction || scriptGenerating.value) return
  scriptGenerating.value = true
  scriptError.value = ''
  scriptMeta.value = ''
  try {
    const response = await ttsApi.generateVoiceScript({
      user_id: userId.value,
      instruction,
    })
    text.value = applyGeneratedScript(text.value, response.text)
    scriptMeta.value = `${response.provider_name} · ${response.model}`
  } catch (error) {
    scriptError.value = error instanceof Error ? error.message : '文案生成失败'
  } finally {
    scriptGenerating.value = false
  }
}

function openVoiceManager(providerId?: TtsProviderId, modelId?: string) {
  const provider = clonedProviders.value.find((item) => item.id === providerId) || clonedProviders.value[0]
  if (provider) {
    voiceForm.provider = provider.id
    voiceForm.bound_model = provider.models.find((model) => model.id === modelId && model.voice_kinds.includes('cloned'))?.id
      || provider.models.find((model) => model.voice_kinds.includes('cloned'))?.id || null
  }
  voiceForm.user_id = userId.value
  voiceManagerMode.value = 'register'
  voiceManagerOpen.value = true
  voiceError.value = ''
  voiceSuccess.value = ''
}

function changeVoiceFormProvider(providerId: TtsProviderId) {
  voiceForm.provider = providerId
  voiceForm.bound_model = voiceFormModels.value[0]?.id || null
}

async function saveVoice() {
  if (!voiceForm.display_name.trim() || !voiceForm.external_voice_id.trim() || !voiceForm.bound_model) {
    voiceError.value = '音色名、音色 ID 和绑定模型都需要填写。'
    return
  }
  savingVoice.value = true
  voiceError.value = ''
  try {
    const created = await ttsApi.createTtsVoice({
      ...voiceForm,
      user_id: userId.value,
      display_name: voiceForm.display_name.trim(),
      external_voice_id: voiceForm.external_voice_id.trim(),
    })
    customVoices.value.unshift(created)
    voiceForm.display_name = ''
    voiceForm.external_voice_id = ''
  } catch (error) {
    voiceError.value = error instanceof Error ? error.message : '保存音色失败'
  } finally {
    savingVoice.value = false
  }
}

async function enrollLiveVoice() {
  voiceError.value = ''
  voiceSuccess.value = ''
  const displayName = liveEnrollmentForm.display_name.trim()
  const prefix = liveEnrollmentForm.prefix.trim()
  const audioUrl = liveEnrollmentForm.audio_url.trim()
  if (!displayName || !/^[A-Za-z0-9]{1,10}$/.test(prefix) || !audioUrl.startsWith('https://')) {
    voiceError.value = '请填写音色名、1–10 位英文或数字前缀，以及完整的 HTTPS 音频地址。'
    return
  }
  savingVoice.value = true
  try {
    const created = await ttsApi.enrollLiveVoice({
      user_id: userId.value,
      display_name: displayName,
      target_model: liveEnrollmentForm.target_model,
      prefix,
      audio_url: audioUrl,
    })
    customVoices.value.unshift(created)
    liveEnrollmentForm.display_name = ''
    liveEnrollmentForm.audio_url = ''
    voiceSuccess.value = `“${created.display_name}”已创建，并同步到 Live。`
  } catch (error) {
    voiceError.value = error instanceof Error ? error.message : 'Live 音色复刻失败'
  } finally {
    liveEnrollmentForm.audio_url = ''
    savingVoice.value = false
  }
}

async function removeVoice(voice: TtsCustomVoice) {
  await ttsApi.deleteTtsVoice(voice.id, userId.value)
  customVoices.value = customVoices.value.filter((item) => item.id !== voice.id)
  for (const track of tracks.value) {
    if (track.voice_id === voice.external_voice_id) track.voice_id = voicesFor(track)[0]?.value || ''
  }
}

function waveform(trackId: string) {
  const seed = [...trackId].reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return Array.from({ length: 42 }, (_, index) => 16 + ((seed + index * 29 + index * index * 3) % 76))
}

onMounted(async () => {
  try {
    const [capabilities, voices] = await Promise.all([
      ttsApi.listTtsCapabilities(),
      ttsApi.listTtsVoices(userId.value),
    ])
    providers.value = capabilities.providers
    customVoices.value = voices
    tracks.value = [makeTrack()]
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '语音工作台加载失败'
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => releaseTrackResults(results.value))
</script>

<template>
  <main class="voice-lab">
    <header class="lab-head">
      <button class="lab-brand" @click="router.push('/toolbox')"><i></i><span>AGENTBI / TOOLBOX</span></button>
      <div class="lab-title"><small>UTILITY 01</small><strong>VOICE LAB</strong></div>
      <div class="head-status"><span><i></i>{{ configuredCount }}/{{ providers.length }} ONLINE</span><button @click="router.push('/chat')">返回 Studio ↗</button></div>
    </header>

    <section v-if="loading" class="lab-loading"><i></i><span>正在校准语音工作台</span></section>
    <section v-else class="lab-grid">
      <aside class="control-rack">
        <div class="rack-intro"><span>CONTROL RACK</span><b>{{ comparison ? `${tracks.length} TRACKS` : 'SINGLE TRACK' }}</b></div>
        <button class="compare-switch" :class="{ active: comparison }" @click="toggleComparison">
          <span><strong>对比模式</strong><small>同一文本，并行试听不同模型</small></span><i><b></b></i>
        </button>

        <div class="track-stack">
          <article v-for="(track, index) in tracks" :key="track.id" class="track-panel">
            <header><span>TRACK {{ String(index + 1).padStart(2, '0') }}</span><b :class="{ offline: !providerFor(track)?.configured }">{{ providerFor(track)?.configured ? 'READY' : 'NO KEY' }}</b><button v-if="comparison && tracks.length > 2" @click="removeTrack(track.id)">×</button></header>
            <label class="select-field"><span>供应商</span><select :value="track.provider" @change="chooseProvider(track, ($event.target as HTMLSelectElement).value as TtsProviderId)"><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.label }}{{ provider.configured ? '' : ' · 未配置' }}</option></select></label>
            <label class="select-field"><span>模型</span><select :value="track.model" @change="chooseModel(track, ($event.target as HTMLSelectElement).value)"><option v-for="model in providerFor(track)?.models" :key="model.id" :value="model.id">{{ model.label }}</option></select></label>
            <label class="select-field voice-field"><span>音色 <button @click.prevent="openVoiceManager(track.provider, track.model)">＋ 添加</button></span><select v-model="track.voice_id"><option value="" disabled>{{ voicesFor(track).length ? '选择音色' : '先添加该模型的音色' }}</option><option v-for="voice in voicesFor(track)" :key="voice.key" :value="voice.value">{{ voice.label }}</option></select><small v-if="track.provider === 'bailian'">CosyVoice 3.5 Plus / Flash 的复刻音色不互通</small></label>
            <div class="parameter-grid">
              <label v-for="parameter in providerFor(track)?.parameters" :key="parameter.key" :class="{ wide: parameter.type === 'text' }">
                <span>{{ parameter.label }}<output v-if="parameter.type === 'number'">{{ track.parameters[parameter.key] }}</output></span>
                <input v-if="parameter.type === 'number'" type="range" :min="parameter.minimum" :max="parameter.maximum" :step="parameter.step" :value="Number(track.parameters[parameter.key])" @input="updateParameter(track, parameter.key, ($event.target as HTMLInputElement).value, true)">
                <select v-else-if="parameter.type === 'select'" :value="String(track.parameters[parameter.key] ?? '')" @change="updateParameter(track, parameter.key, ($event.target as HTMLSelectElement).value)"><option v-for="option in parameter.options" :key="option.value" :value="option.value">{{ option.label }}</option></select>
                <input v-else type="text" :value="String(track.parameters[parameter.key] ?? '')" placeholder="可选" @input="updateParameter(track, parameter.key, ($event.target as HTMLInputElement).value)">
              </label>
            </div>
            <label class="format-row"><span>输出格式</span><span><button v-for="format in providerFor(track)?.audio_formats" :key="format" :class="{ active: track.audio_format === format }" @click="track.audio_format = format as TtsAudioFormat">{{ format }}</button></span></label>
          </article>
        </div>
        <button v-if="comparison && tracks.length < 4" class="add-track" @click="addTrack">＋ 添加一条对比轨道</button>
        <button class="manage-voices" @click="openVoiceManager()">管理我的音色 <span>{{ customVoices.length }}</span></button>
      </aside>

      <section class="script-desk">
        <header class="desk-head"><div><span>MASTER SCRIPT</span><strong>让所有轨道说同一段话。</strong></div><p>{{ text.length }} / 10000</p></header>
        <form class="script-generator" @submit.prevent="generateScript">
          <label for="script-instruction"><span>AI WRITER</span><b>告诉 Studio 模型你想要什么文案</b></label>
          <textarea id="script-instruction" v-model="scriptInstruction" maxlength="4000" rows="2" placeholder="例如：写一段 30 秒的深夜城市纪录片旁白，克制、冷静、有画面感。"></textarea>
          <button type="submit" :disabled="!scriptInstruction.trim() || scriptGenerating">
            <i></i>{{ scriptGenerating ? '生成中…' : '生成并覆盖正文' }}
          </button>
          <small v-if="scriptMeta">已使用 {{ scriptMeta }}</small>
          <small v-else>复用 Studio 当前聊天模型与温度，不写入会话</small>
        </form>
        <p v-if="scriptError" class="workbench-error script-error">{{ scriptError }} · 原文已保留</p>
        <div class="editor-wrap"><textarea v-model="text" maxlength="10000" placeholder="在这里输入需要合成的文本……"></textarea><span class="editor-corner">TXT · UTF-8</span></div>
        <p v-if="loadError" class="workbench-error">{{ loadError }}</p>
        <div class="render-bar"><div><span>RENDER QUEUE</span><strong>{{ tracks.length }} 条轨道 · {{ successfulResults }} 个结果</strong></div><button :disabled="generating" @click="runSynthesis"><i></i>{{ generating ? '正在生成…' : comparison ? `并行生成 ${tracks.length} 条音频` : '生成语音' }}</button></div>

        <section class="result-grid" :class="{ comparison }">
          <article v-for="(track, index) in tracks" :key="`result-${track.id}`" class="result-card" :data-status="resultFor(track.id)?.status || 'idle'">
            <header><div><span>OUTPUT {{ String(index + 1).padStart(2, '0') }}</span><strong>{{ providerFor(track)?.label }}</strong></div><small>{{ resultFor(track.id)?.elapsedMs ? `${resultFor(track.id)?.elapsedMs} MS` : track.model }}</small></header>
            <div v-if="resultFor(track.id)?.status === 'loading'" class="result-loading"><div><i v-for="n in 24" :key="n" :style="{ height: `${16 + ((n * 31) % 68)}%` }"></i></div><span>GENERATING AUDIO</span></div>
            <div v-else-if="resultFor(track.id)?.status === 'error'" class="result-error"><b>!</b><span><strong>这条轨道失败了</strong><small>{{ resultFor(track.id)?.error }}</small></span></div>
            <template v-else-if="resultFor(track.id)?.audioUrl"><div class="waveform"><i v-for="(height, n) in waveform(track.id)" :key="n" :style="{ height: `${height}%` }"></i></div><audio :src="resultFor(track.id)?.audioUrl" controls preload="metadata"></audio><footer><span>{{ track.audio_format.toUpperCase() }} · {{ track.voice_id }}</span><a :href="resultFor(track.id)?.audioUrl" :download="`voice-lab-${index + 1}.${track.audio_format}`">下载音频 ↓</a></footer></template>
            <div v-else class="result-empty"><i>↗</i><span>生成后在这里试听与下载</span></div>
          </article>
        </section>
      </section>
    </section>

    <Transition name="drawer">
      <div v-if="voiceManagerOpen" class="drawer-backdrop" @click.self="voiceManagerOpen = false">
        <aside class="voice-drawer">
          <header><div><span>VOICE CATALOG</span><h2>添加我的音色</h2></div><button @click="voiceManagerOpen = false">×</button></header>
          <div class="drawer-scroll">
            <nav class="voice-mode-tabs">
              <button :class="{ active: voiceManagerMode === 'register' }" @click="voiceManagerMode = 'register'; voiceError = ''; voiceSuccess = ''"><span>01</span>登记已有音色</button>
              <button :class="{ active: voiceManagerMode === 'enroll-live' }" @click="voiceManagerMode = 'enroll-live'; voiceError = ''; voiceSuccess = ''"><span>02</span>Live 音色复刻</button>
            </nav>

            <template v-if="voiceManagerMode === 'register'">
              <p class="drawer-note">界面用“音色名”帮助识别；发送给供应商时使用“音色 ID”。已有复刻结果可直接登记。</p>
              <div class="voice-form">
                <label><span>供应商</span><select :value="voiceForm.provider" @change="changeVoiceFormProvider(($event.target as HTMLSelectElement).value as TtsProviderId)"><option v-for="provider in clonedProviders" :key="provider.id" :value="provider.id">{{ provider.label }}</option></select></label>
                <label><span>绑定模型</span><select v-model="voiceForm.bound_model"><option v-for="model in voiceFormModels" :key="model.id" :value="model.id">{{ model.label }}</option></select></label>
                <label><span>音色名</span><input v-model="voiceForm.display_name" maxlength="80" placeholder="例如：电影旁白"></label>
                <label><span>音色 ID</span><input v-model="voiceForm.external_voice_id" maxlength="256" placeholder="供应商控制台中的 Voice ID"></label>
                <p v-if="voiceError">{{ voiceError }}</p>
                <button :disabled="savingVoice" @click="saveVoice">{{ savingVoice ? '保存中…' : '保存音色资产' }}</button>
              </div>
            </template>

            <template v-else>
              <p class="drawer-note live-note"><b>LIVE ENROLLMENT</b>粘贴 OSS 的 HTTPS 地址。Flash 与 Plus 音色不互通；签名 URL 仅用于本次请求，不会保存。</p>
              <div class="voice-form enrollment-form">
                <label><span>音色名</span><input v-model="liveEnrollmentForm.display_name" maxlength="80" placeholder="例如：夜间电台"></label>
                <label><span>目标模型</span><select v-model="liveEnrollmentForm.target_model"><option v-for="model in liveEnrollmentModels" :key="model.id" :value="model.id">{{ model.label }}</option></select></label>
                <label><span>英文前缀</span><input v-model="liveEnrollmentForm.prefix" maxlength="10" pattern="[A-Za-z0-9]+" placeholder="livevoice"></label>
                <label class="wide"><span>OSS 音频 URL</span><textarea v-model="liveEnrollmentForm.audio_url" maxlength="4096" rows="4" spellcheck="false" placeholder="https://xxx.oss-cn-beijing.aliyuncs.com/sample.mp3?..."></textarea><small>支持百炼要求的 WAV / MP3 / M4A；建议 10–20 秒清晰人声。</small></label>
                <p v-if="voiceError">{{ voiceError }}</p>
                <p v-if="voiceSuccess" class="voice-success">{{ voiceSuccess }}</p>
                <button :disabled="savingVoice" @click="enrollLiveVoice">{{ savingVoice ? '正在复刻并登记…' : '创建 Live 音色' }}</button>
              </div>
            </template>

            <section class="voice-assets"><header><span>已登记音色</span><b>{{ customVoices.length }}</b></header><article v-for="voice in customVoices" :key="voice.id"><div><strong>{{ voice.display_name }}</strong><small>{{ providers.find((item) => item.id === voice.provider)?.label }} · {{ voice.bound_model }}</small><code>{{ voice.external_voice_id }}</code></div><button @click="removeVoice(voice)">删除</button></article><p v-if="!customVoices.length">还没有添加自定义音色。</p></section>
          </div>
        </aside>
      </div>
    </Transition>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
*{box-sizing:border-box}.voice-lab{--ink:#11110f;--panel:#181816;--line:#34332f;--paper:#efede6;--acid:#d9ff36;--muted:#77746c;min-height:100vh;background:var(--ink);color:var(--paper);font-family:Manrope,sans-serif}.lab-head{position:sticky;z-index:10;top:0;height:70px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 25px;border-bottom:1px solid var(--line);background:rgba(17,17,15,.92);backdrop-filter:blur(16px)}button,select,input,textarea{font:inherit}.lab-brand{display:flex;align-items:center;gap:9px;border:0;background:transparent;color:#96938a;font:8px 'DM Mono';letter-spacing:.12em;cursor:pointer}.lab-brand i{width:14px;height:14px;border:1px solid var(--acid);box-shadow:3px 3px 0 var(--acid)}.lab-title{text-align:center}.lab-title small,.lab-title strong{display:block}.lab-title small{color:#5f5d57;font:6px 'DM Mono';letter-spacing:.18em}.lab-title strong{margin-top:3px;font:700 13px Manrope;letter-spacing:.13em}.head-status{justify-self:end;display:flex;align-items:center;gap:8px}.head-status span,.head-status button{height:30px;display:flex;align-items:center;gap:7px;padding:0 10px;border:1px solid var(--line);background:transparent;color:#6c6962;font:7px 'DM Mono';letter-spacing:.08em}.head-status span i{width:5px;height:5px;border-radius:50%;background:var(--acid);box-shadow:0 0 8px var(--acid)}.head-status button{cursor:pointer}.head-status button:hover{color:var(--acid);border-color:var(--acid)}.lab-loading{height:calc(100vh - 70px);display:flex;justify-content:center;align-items:center;gap:12px;color:#6d6a63;font:9px 'DM Mono';letter-spacing:.12em}.lab-loading i{width:12px;height:12px;border:1px solid #4a4944;border-top-color:var(--acid);border-radius:50%;animation:spin .8s linear infinite}.lab-grid{min-height:calc(100vh - 70px);display:grid;grid-template-columns:370px minmax(0,1fr)}.control-rack{border-right:1px solid var(--line);background:#141412;padding:19px;overflow-y:auto;max-height:calc(100vh - 70px);scrollbar-width:thin;scrollbar-color:#3b3a35 transparent}.rack-intro{display:flex;justify-content:space-between;color:#55534e;font:7px 'DM Mono';letter-spacing:.13em;margin:2px 2px 14px}.rack-intro b{color:#77746d;font-weight:400}.compare-switch{width:100%;display:grid;grid-template-columns:1fr auto;align-items:center;padding:13px;border:1px solid #353530;background:#191917;color:#a5a299;text-align:left;cursor:pointer}.compare-switch span strong,.compare-switch span small{display:block}.compare-switch strong{font-size:10px}.compare-switch small{margin-top:4px;color:#5d5b55;font-size:8px}.compare-switch>i{width:37px;height:20px;padding:3px;border-radius:20px;background:#2b2b27}.compare-switch>i b{display:block;width:14px;height:14px;border-radius:50%;background:#6d6a63;transition:.22s}.compare-switch.active{border-color:#596322}.compare-switch.active>i{background:#4d5b1e}.compare-switch.active>i b{transform:translateX(17px);background:var(--acid)}.track-stack{display:grid;gap:9px;margin-top:9px}.track-panel{border:1px solid #34332f;background:#1a1a18;padding:13px}.track-panel>header{display:grid;grid-template-columns:1fr auto auto;align-items:center;padding-bottom:11px;border-bottom:1px solid #33322e;color:#6a6861;font:7px 'DM Mono';letter-spacing:.13em}.track-panel>header b{color:var(--acid);font-weight:400}.track-panel>header b.offline{color:#ff796f}.track-panel>header button{margin-left:8px;border:0;background:transparent;color:#77746c;cursor:pointer}.select-field{display:grid;gap:6px;margin-top:13px}.select-field>span,.parameter-grid label>span,.format-row>span:first-child{color:#68665f;font:7px 'DM Mono';letter-spacing:.1em}.select-field>span button{float:right;border:0;background:transparent;color:var(--acid);font:7px 'DM Mono';cursor:pointer}.select-field select,.parameter-grid select,.parameter-grid input[type=text]{width:100%;height:34px;border:0;border-bottom:1px solid #44423d;outline:0;background:#151513;color:#d1cec5;padding:0 5px;font-size:9px}.select-field select:focus,.parameter-grid input:focus{border-bottom-color:var(--acid)}.voice-field>small{color:#5f5c55;font:7px/1.45 'DM Mono'}.parameter-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px}.parameter-grid label{display:grid;gap:6px}.parameter-grid label.wide{grid-column:1/-1}.parameter-grid output{float:right;color:#b8d82f}.parameter-grid input[type=range]{width:100%;height:10px;accent-color:var(--acid)}.format-row{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:10px;margin-top:15px}.format-row>span:last-child{display:flex;justify-content:flex-end;gap:3px}.format-row button{border:1px solid #3c3b36;background:transparent;color:#68665f;padding:5px 7px;font:7px 'DM Mono';text-transform:uppercase;cursor:pointer}.format-row button.active{border-color:var(--acid);color:var(--acid)}.add-track,.manage-voices{width:100%;height:39px;margin-top:9px;border:1px dashed #45433d;background:transparent;color:#77746d;font:8px 'DM Mono';cursor:pointer}.add-track:hover{border-color:var(--acid);color:var(--acid)}.manage-voices{display:flex;align-items:center;justify-content:space-between;border-style:solid;padding:0 12px;text-align:left}.manage-voices span{display:grid;place-items:center;width:20px;height:20px;background:#2c2b27;color:var(--acid)}.script-desk{min-width:0;padding:28px clamp(24px,4vw,62px) 65px;background:radial-gradient(circle at 92% 4%,rgba(217,255,54,.055),transparent 26%),#11110f;overflow-y:auto;max-height:calc(100vh - 70px)}.desk-head{display:flex;justify-content:space-between;align-items:end;margin-bottom:16px}.desk-head span{color:var(--acid);font:7px 'DM Mono';letter-spacing:.15em}.desk-head strong{display:block;margin-top:5px;font:600 clamp(20px,2.2vw,31px) 'Playfair Display';letter-spacing:-.03em}.desk-head p{color:#55534e;font:7px 'DM Mono'}.script-generator{display:grid;grid-template-columns:minmax(150px,.55fr) minmax(260px,1.45fr) auto;align-items:center;gap:10px;margin-bottom:14px;padding:10px;border:1px solid #34332f;background:#171715}.script-generator label{padding-left:4px}.script-generator label span,.script-generator label b{display:block}.script-generator label span{color:var(--acid);font:7px 'DM Mono';letter-spacing:.14em}.script-generator label b{margin-top:4px;color:#87847c;font-size:9px;font-weight:500}.script-generator textarea{width:100%;min-height:48px;max-height:108px;resize:vertical;border:1px solid #403f39;outline:0;background:#11110f;color:#d4d0c7;padding:9px 11px;font:9px/1.55 Manrope}.script-generator textarea:focus{border-color:#738224;box-shadow:inset 2px 0 var(--acid)}.script-generator textarea::placeholder{color:#57554f}.script-generator button{height:48px;padding:0 16px;border:1px solid var(--acid);background:transparent;color:var(--acid);font:700 8px Manrope;white-space:nowrap;cursor:pointer;transition:.18s}.script-generator button i{display:inline-block;width:5px;height:5px;margin-right:7px;background:currentColor;box-shadow:5px -5px 0 rgba(217,255,54,.32)}.script-generator button:hover:not(:disabled){background:var(--acid);color:#111}.script-generator button:disabled{border-color:#3b3a35;color:#55534e;cursor:not-allowed}.script-generator>small{grid-column:2/-1;color:#5d5a54;font:7px 'DM Mono';letter-spacing:.04em}.editor-wrap{position:relative;min-height:250px;border:1px solid #bbb8af;background:var(--paper);box-shadow:8px 8px 0 rgba(217,255,54,.86)}.editor-wrap textarea{width:100%;min-height:300px;resize:vertical;border:0;outline:0;background:transparent;color:#171714;padding:25px 27px 45px;font:500 16px/1.85 Manrope}.editor-wrap textarea::placeholder{color:#aaa69d}.editor-corner{position:absolute;right:15px;bottom:12px;color:#8f8c84;font:7px 'DM Mono';letter-spacing:.1em}.workbench-error{margin:17px 0 -5px;color:#ff8e84;font:8px 'DM Mono'}.script-error{margin:-4px 0 12px}.render-bar{display:flex;justify-content:space-between;align-items:center;margin:30px 0 17px;padding:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.render-bar span,.render-bar strong{display:block}.render-bar span{color:#55534e;font:7px 'DM Mono';letter-spacing:.13em}.render-bar strong{margin-top:4px;color:#88857d;font-size:9px}.render-bar>button{min-width:190px;height:44px;border:0;background:var(--acid);color:#141510;font:700 9px Manrope;cursor:pointer}.render-bar>button i{display:inline-block;width:6px;height:6px;margin-right:8px;background:#111}.render-bar>button:disabled{opacity:.55;cursor:wait}.result-grid{display:grid;grid-template-columns:1fr;gap:10px}.result-grid.comparison{grid-template-columns:repeat(2,minmax(0,1fr))}.result-card{min-height:245px;border:1px solid var(--line);background:#181816;padding:17px}.result-card>header{display:flex;justify-content:space-between;align-items:start}.result-card>header span,.result-card>header strong{display:block}.result-card>header span{color:#5d5b55;font:7px 'DM Mono';letter-spacing:.13em}.result-card>header strong{margin-top:4px;font-size:11px}.result-card>header small{max-width:52%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#595750;font:7px 'DM Mono'}.result-empty{height:170px;display:grid;place-content:center;justify-items:center;gap:12px;color:#4e4c47;font:8px 'DM Mono'}.result-empty i{width:34px;height:34px;display:grid;place-items:center;border:1px solid #363530;border-radius:50%;font-style:normal}.waveform,.result-loading>div{height:100px;display:flex;align-items:center;gap:2px;margin-top:16px}.waveform i,.result-loading i{flex:1;min-width:1px;background:#8ca620}.result-card audio{width:100%;height:33px;filter:invert(1) grayscale(1);opacity:.75}.result-card footer{display:flex;justify-content:space-between;gap:12px;margin-top:12px}.result-card footer span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#55534e;font:7px 'DM Mono'}.result-card footer a{flex:0 0 auto;color:var(--acid);font:7px 'DM Mono';text-decoration:none}.result-loading>div i{background:#5d6c27;animation:levels .8s ease-in-out infinite alternate}.result-loading>div i:nth-child(3n){animation-delay:.2s}.result-loading>span{display:block;text-align:center;color:#67732f;font:7px 'DM Mono';letter-spacing:.14em}.result-error{height:170px;display:flex;align-items:center;justify-content:center;gap:13px}.result-error>b{width:32px;height:32px;display:grid;place-items:center;border:1px solid #7e403b;color:#ff796f}.result-error strong,.result-error small{display:block}.result-error strong{color:#d39791;font-size:10px}.result-error small{max-width:300px;margin-top:5px;color:#785b57;font:7px/1.5 'DM Mono'}.drawer-backdrop{position:fixed;z-index:30;inset:0;display:flex;justify-content:flex-end;background:rgba(0,0,0,.64);backdrop-filter:blur(7px)}.voice-drawer{width:min(520px,100%);height:100%;display:grid;grid-template-rows:auto minmax(0,1fr);background:#171715;border-left:1px solid #48463f;box-shadow:-30px 0 80px #000}.voice-drawer>header{display:flex;justify-content:space-between;padding:27px;border-bottom:1px solid #34332f}.voice-drawer>header span{color:var(--acid);font:7px 'DM Mono';letter-spacing:.14em}.voice-drawer h2{margin:7px 0 0;font:600 30px 'Playfair Display'}.voice-drawer>header button{width:34px;height:34px;border:1px solid #3e3d38;background:transparent;color:#7d7a72;font-size:18px;cursor:pointer}.drawer-scroll{overflow-y:auto;padding:24px 27px 50px;scrollbar-width:thin;scrollbar-color:#46443e transparent}.drawer-note{margin:0 0 22px;padding:13px;border-left:2px solid var(--acid);background:#1e1e1b;color:#89867d;font:8px/1.7 'DM Mono'}.voice-form{display:grid;grid-template-columns:1fr 1fr;gap:12px}.voice-form label{display:grid;gap:7px}.voice-form label span{color:#716e67;font:7px 'DM Mono';letter-spacing:.09em}.voice-form input,.voice-form select{height:39px;border:1px solid #403f39;outline:0;background:#11110f;color:#d2cfc6;padding:0 10px;font-size:9px}.voice-form input:focus,.voice-form select:focus{border-color:var(--acid)}.voice-form>p{grid-column:1/-1;margin:0;color:#ff8278;font:8px 'DM Mono'}.voice-form>button{grid-column:1/-1;height:42px;margin-top:4px;border:0;background:var(--acid);color:#111;font-weight:700;font-size:9px;cursor:pointer}.voice-assets{margin-top:34px}.voice-assets>header{display:flex;justify-content:space-between;padding-bottom:11px;border-bottom:1px solid #3c3a35;color:#77746d;font:8px 'DM Mono'}.voice-assets>header b{color:var(--acid)}.voice-assets article{display:grid;grid-template-columns:1fr auto;gap:12px;padding:15px 0;border-bottom:1px solid #302f2b}.voice-assets strong,.voice-assets small,.voice-assets code{display:block}.voice-assets strong{font-size:10px}.voice-assets small{margin-top:4px;color:#69665f;font:7px 'DM Mono'}.voice-assets code{max-width:360px;margin-top:8px;overflow:hidden;text-overflow:ellipsis;color:#4e4c47;font:7px 'DM Mono'}.voice-assets article button{align-self:center;border:0;background:transparent;color:#8e5b56;font:7px 'DM Mono';cursor:pointer}.voice-assets>p{color:#57554f;font:8px 'DM Mono';padding:25px 0}.drawer-enter-active,.drawer-leave-active{transition:opacity .2s}.drawer-enter-active .voice-drawer,.drawer-leave-active .voice-drawer{transition:transform .28s cubic-bezier(.2,.8,.2,1)}.drawer-enter-from,.drawer-leave-to{opacity:0}.drawer-enter-from .voice-drawer,.drawer-leave-to .voice-drawer{transform:translateX(70px)}@keyframes spin{to{transform:rotate(360deg)}}@keyframes levels{to{height:22%!important}}@media(max-width:1040px){.lab-grid{grid-template-columns:330px minmax(0,1fr)}.result-grid.comparison{grid-template-columns:1fr}.script-desk{padding-inline:28px}.script-generator{grid-template-columns:1fr auto}.script-generator label{grid-column:1/-1}.script-generator>small{grid-column:1/-1}}@media(max-width:760px){.lab-head{grid-template-columns:1fr auto}.lab-title{display:none}.head-status span{display:none}.lab-grid{display:block}.control-rack,.script-desk{max-height:none}.control-rack{border-right:0;border-bottom:1px solid var(--line)}.script-desk{padding:28px 18px 55px}.script-generator{grid-template-columns:1fr}.script-generator label,.script-generator button,.script-generator>small{grid-column:1}.script-generator button{width:100%}.editor-wrap textarea{min-height:230px}.render-bar{align-items:stretch;flex-direction:column;gap:13px}.render-bar>button{width:100%}.voice-form{grid-template-columns:1fr}.voice-form>p,.voice-form>button{grid-column:1}.result-grid.comparison{grid-template-columns:1fr}}
.voice-mode-tabs{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:18px;padding:4px;border:1px solid #35342f;background:#11110f}.voice-mode-tabs button{height:42px;border:0;background:transparent;color:#67645d;font:8px 'DM Mono';cursor:pointer}.voice-mode-tabs button span{margin-right:7px;color:#45433e}.voice-mode-tabs button.active{background:#25251f;color:var(--acid);box-shadow:inset 0 -1px var(--acid)}.voice-mode-tabs button.active span{color:#8da220}.live-note{display:grid;gap:5px}.live-note b{color:var(--acid);font:7px 'DM Mono';letter-spacing:.14em}.enrollment-form label.wide{grid-column:1/-1}.enrollment-form textarea{width:100%;resize:vertical;min-height:92px;border:1px solid #403f39;outline:0;background:#11110f;color:#d2cfc6;padding:10px;font:8px/1.55 'DM Mono'}.enrollment-form textarea:focus{border-color:var(--acid)}.enrollment-form label small{color:#5d5a53;font:7px/1.55 'DM Mono'}.voice-form>p.voice-success{color:#b9d936}
</style>
