<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as providers from '@/api/providers'
import * as modelRoutesApi from '@/api/model-routes'
import type { ModelRouteRole, ProviderProfile } from '@/api/chat-types'
import { useChatStore } from '@/stores/chat'
import {
  CONTEXT_TURN_STEPS,
  contextTurnLabel,
  contextTurnSliderIndex,
  contextTurnsFromSlider,
} from '@/utils/context-turns'
import { loadSettingsResources } from '@/utils/settings-load'

const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const userId = computed(() => auth.email || 'local-user')
const profiles = ref<ProviderProfile[]>([])
const busy = ref('')
const error = ref('')
const form = ref({ name: '', base_url: '', api_key: '', default_model: '' })
const routeDefinitions: Array<{ role: ModelRouteRole; index: string; title: string; detail: string }> = [
  { role: 'embedding', index: 'VEC', title: '向量模型', detail: '历史会话语义索引与检索' },
  { role: 'compression', index: 'ZIP', title: '压缩模型', detail: '长会话的增量上下文摘要' },
  { role: 'memory', index: 'MEM', title: '记忆模型', detail: '提炼跨会话稳定事实与偏好' },
  { role: 'title', index: 'TTL', title: '标题模型', detail: '首轮完成后生成会话标题' },
]
const routeDrafts = ref<Record<ModelRouteRole, { providerId: string; model: string }>>({
  embedding: { providerId: '', model: '' },
  compression: { providerId: '', model: '' },
  memory: { providerId: '', model: '' },
  title: { providerId: '', model: '' },
})
const activeProfile = computed(() => profiles.value.find((profile) => profile.id === chat.preferences.providerId))
const contextSlider = computed({
  get: () => contextTurnSliderIndex(chat.preferences.contextTurns),
  set: (index: number) => { chat.preferences.contextTurns = contextTurnsFromSlider(index) },
})
const contextLabel = computed(() => contextTurnLabel(chat.preferences.contextTurns))

async function load() {
  const result = await loadSettingsResources(
    providers.listProviders,
    () => modelRoutesApi.listModelRoutes(userId.value),
  )
  profiles.value = result.providers
  for (const route of result.routes)
    routeDrafts.value[route.role] = { providerId: route.provider_id, model: route.model }
  error.value = result.providerError || result.routeError
}
function routeModels(role: ModelRouteRole) {
  return profiles.value.find((profile) => profile.id === routeDrafts.value[role].providerId)?.available_models || []
}
function selectRouteProvider(role: ModelRouteRole) {
  const models = routeModels(role)
  routeDrafts.value[role].model = models[0] || ''
}
async function saveRoute(role: ModelRouteRole) {
  const draft = routeDrafts.value[role]
  if (!draft.providerId || !draft.model) return
  busy.value = `route-${role}`
  try { await modelRoutesApi.saveModelRoute(userId.value, role, draft.providerId, draft.model) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '后台模型保存失败' }
  finally { busy.value = '' }
}
async function clearRoute(role: ModelRouteRole) {
  busy.value = `route-${role}`
  try {
    await modelRoutesApi.deleteModelRoute(userId.value, role)
    routeDrafts.value[role] = { providerId: '', model: '' }
  } finally { busy.value = '' }
}
async function add() {
  if (!form.value.name || !form.value.base_url || !form.value.api_key) return
  busy.value = 'add'
  try {
    const profile = await providers.createProvider(form.value)
    form.value = { name: '', base_url: '', api_key: '', default_model: '' }
    chat.preferences.providerId = profile.id
    chat.preferences.model = profile.default_model || undefined
    await load()
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '保存失败' }
  finally { busy.value = '' }
}
async function refresh(id: string) {
  busy.value = id
  try {
    const profile = await providers.refreshModels(id)
    if (chat.preferences.providerId === id && !chat.preferences.model) chat.preferences.model = profile.available_models[0]
    await load()
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '刷新失败' }
  finally { busy.value = '' }
}
async function remove(id: string) {
  await providers.deleteProvider(id)
  if (chat.preferences.providerId === id) {
    chat.preferences.providerId = undefined
    chat.preferences.model = undefined
  }
  await load()
}

onMounted(async () => { await chat.restorePreferences(userId.value); await load() })
</script>

<template>
  <main class="settings">
    <header>
      <button class="back" @click="router.push('/chat')">← 返回工作台</button>
      <p>MODEL STUDIO / 01</p>
      <h1>模型，<em>由你定义。</em></h1>
      <span>连接任意 OpenAI-compatible 端点；模型列表从提供商实时获取。</span>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <section class="layout">
      <form class="form" @submit.prevent="add">
        <h2>接入新端点</h2>
        <label>显示名称<input v-model="form.name" placeholder="例如 DeepSeek" /></label>
        <label>Base URL<input v-model="form.base_url" placeholder="https://api.example.com/v1" /></label>
        <label>API Key<input v-model="form.api_key" type="password" placeholder="sk-…" /></label>
        <label>默认模型（可稍后刷新选择）<input v-model="form.default_model" placeholder="deepseek-chat" /></label>
        <button :disabled="busy === 'add'">{{ busy === 'add' ? '连接中…' : '保存提供商 →' }}</button>
      </form>

      <section class="profiles">
        <div class="profiles-head"><h2>当前对话配置</h2><span>LIVE</span></div>
        <div class="runtime-controls">
          <label>提供商
            <select v-model="chat.preferences.providerId"><option :value="undefined">选择提供商</option><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select>
          </label>
          <label>模型
            <select v-model="chat.preferences.model" :disabled="!activeProfile"><option :value="undefined">选择模型</option><option v-for="model in activeProfile?.available_models || []" :key="model" :value="model">{{ model }}</option></select>
          </label>
          <label>温度 <output>{{ chat.preferences.temperature.toFixed(1) }}</output><input v-model.number="chat.preferences.temperature" type="range" min="0" max="2" step="0.1" /></label>
          <label>上下文轮次 <output>{{ contextLabel }}</output><input v-model.number="contextSlider" type="range" min="0" :max="CONTEXT_TURN_STEPS.length - 1" step="1" /></label>
        </div>
        <p class="context-note">按 2× 档位扩展：2 → 4 → 8 → 16 → 32 → 64 → 128；最右侧不截断历史上下文。</p>
        <p class="apply-note">这些参数会用于下一次发送；新建会话会记住当前选择。</p>

        <div class="profiles-head task-head"><div><p>BACKGROUND ROUTING</p><h2>后台模型分工</h2></div><span>04</span></div>
        <p class="route-intro">聊天模型只负责当前回复。把索引、压缩、记忆与标题交给更轻量或更专门的模型。</p>
        <div class="route-grid">
          <article v-for="definition in routeDefinitions" :key="definition.role" class="route-card">
            <div class="route-card-head"><b>{{ definition.index }}</b><div><h3>{{ definition.title }}</h3><p>{{ definition.detail }}</p></div></div>
            <label>提供商
              <select v-model="routeDrafts[definition.role].providerId" @change="selectRouteProvider(definition.role)">
                <option value="">未配置</option><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option>
              </select>
            </label>
            <label>模型
              <select v-model="routeDrafts[definition.role].model" :disabled="!routeDrafts[definition.role].providerId">
                <option value="">选择模型</option><option v-for="model in routeModels(definition.role)" :key="model" :value="model">{{ model }}</option>
              </select>
            </label>
            <div class="route-actions"><button :disabled="busy === `route-${definition.role}` || !routeDrafts[definition.role].model" @click="saveRoute(definition.role)">保存路由</button><button class="route-clear" :disabled="!routeDrafts[definition.role].providerId" @click="clearRoute(definition.role)">清除</button></div>
          </article>
        </div>

        <div class="profiles-head list-head"><h2>已连接节点</h2><span>{{ profiles.length.toString().padStart(2, '0') }}</span></div>
        <article v-for="profile in profiles" :key="profile.id" class="profile">
          <div><p>{{ profile.name }}</p><code>{{ profile.base_url }}</code></div>
          <div class="profile-actions"><button @click="refresh(profile.id)">{{ busy === profile.id ? '同步中' : '刷新模型' }}</button><button class="remove" @click="remove(profile.id)">×</button></div>
          <div class="model-list"><button v-for="model in profile.available_models" :key="model" :class="{ selected: chat.preferences.model === model }" @click="chat.preferences.providerId = profile.id; chat.preferences.model = model">{{ model }}</button><i v-if="!profile.available_models.length">尚未同步模型列表</i></div>
        </article>
        <p v-if="!profiles.length" class="no-profiles">配置第一个端点后，聊天页即可开始工作。</p>
      </section>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.settings{min-height:100vh;background:#141414;color:#eeece6;padding:44px clamp(22px,8vw,120px);font-family:Manrope,sans-serif}.settings header{max-width:720px;margin-bottom:52px}.back{border:0;background:transparent;color:#b3b0a8;padding:0;margin-bottom:50px;font:11px 'DM Mono';cursor:pointer}.back:hover{color:#d9ff36}.settings header p{color:#d9ff36;font:10px 'DM Mono';letter-spacing:.16em}.settings h1{font:600 clamp(46px,7vw,86px)/.95 'Playfair Display';letter-spacing:-.06em;margin:13px 0}.settings h1 em{color:#8d8b83}.settings header>span{display:block;color:#aaa69d;font-size:13px;margin-top:22px}.layout{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(0,1.6fr);gap:70px;max-width:1200px}.form{background:#eeece6;color:#141414;padding:28px;align-self:start;box-shadow:8px 8px 0 #d9ff36}.form h2,.profiles h2{margin:0 0 22px;font-size:14px}.form label,.runtime-controls label{display:grid;gap:7px;font:10px 'DM Mono';letter-spacing:.08em;margin-top:16px}.form input,.runtime-controls select{border:0;border-bottom:1px solid #aaa79e;background:transparent;padding:9px 0;outline:0;font:13px Manrope}.form button{border:0;background:#141414;color:#fff;width:100%;padding:13px;margin-top:25px;font:700 12px Manrope;cursor:pointer}.profiles-head{display:flex;justify-content:space-between;border-bottom:1px solid #444;padding-bottom:12px}.profiles-head span{color:#d9ff36;font:12px 'DM Mono'}.runtime-controls{display:grid;grid-template-columns:1fr 1fr;gap:0 24px;padding:8px 0 10px}.runtime-controls select{color:#f0eee7;border-color:#555}.runtime-controls output{float:right;color:#d9ff36}.runtime-controls input[type=range]{accent-color:#d9ff36;width:100%}.context-note,.apply-note{font:10px/1.6 'DM Mono';color:#88847c;margin:5px 0}.context-note{color:#aaa69d}.apply-note{margin-bottom:28px}.list-head{margin-top:10px}.profile{border-bottom:1px solid #333;padding:19px 0;display:grid;grid-template-columns:1fr auto;gap:14px}.profile p{margin:0 0 5px;font-weight:700}.profile code{color:#949188;font:10px 'DM Mono'}.profile-actions{display:flex;gap:7px}.profile-actions button{align-self:start;background:transparent;border:1px solid #555;color:#ddd;padding:7px 9px;font:10px 'DM Mono';cursor:pointer}.profile-actions button:hover{border-color:#d9ff36;color:#d9ff36}.profile-actions .remove{font-size:16px;padding:2px 8px}.model-list{grid-column:1/-1;display:flex;gap:6px;flex-wrap:wrap}.model-list button{border:1px solid #3a3a3a;background:transparent;padding:4px 7px;color:#cbc8bf;font:9px 'DM Mono';cursor:pointer}.model-list button.selected,.model-list button:hover{border-color:#d9ff36;color:#d9ff36}.model-list i,.no-profiles{color:#777;font:11px 'DM Mono';font-style:normal}.error{color:#ff7a70;font:11px 'DM Mono'}@media(max-width:750px){.settings{padding:27px 20px}.layout{grid-template-columns:1fr;gap:42px}.back{margin-bottom:32px}.runtime-controls{grid-template-columns:1fr}}
.task-head{align-items:end;margin-top:38px}.task-head>div>p{margin:0 0 4px;color:#d9ff36;font:8px 'DM Mono';letter-spacing:.15em}.task-head h2{margin:0}.route-intro{max-width:580px;color:#8e8a82;font:10px/1.7 'DM Mono'}.route-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:20px 0 38px;background:#414141;border:1px solid #414141}.route-card{position:relative;padding:18px;background:#191919;overflow:hidden}.route-card:after{position:absolute;right:-20px;top:-30px;color:#222;font:800 82px/1 Manrope;content:'+';pointer-events:none}.route-card-head{position:relative;z-index:1;display:grid;grid-template-columns:34px 1fr;gap:10px;align-items:start}.route-card-head>b{display:grid;place-items:center;width:32px;height:32px;background:#d9ff36;color:#111;font:8px 'DM Mono'}.route-card h3{margin:0;color:#efede6;font-size:12px}.route-card p{margin:4px 0 0;color:#77736b;font:8px/1.5 'DM Mono'}.route-card label{position:relative;z-index:1;display:grid;gap:5px;margin-top:14px;color:#807d76;font:8px 'DM Mono';letter-spacing:.08em}.route-card select{width:100%;border:0;border-bottom:1px solid #474747;background:#191919;color:#d6d3cb;padding:7px 0;outline:0;font:10px Manrope}.route-actions{position:relative;z-index:1;display:flex;gap:7px;margin-top:16px}.route-actions button{border:1px solid #5b5b5b;background:transparent;color:#d9ff36;padding:7px 10px;font:8px 'DM Mono';cursor:pointer}.route-actions button:disabled{cursor:not-allowed;opacity:.35}.route-actions .route-clear{border-color:transparent;color:#777}@media(max-width:750px){.route-grid{grid-template-columns:1fr}}
</style>
