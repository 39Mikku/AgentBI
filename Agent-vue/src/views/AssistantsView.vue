<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '@/api/assistants'
import { useAuthStore } from '@/stores/auth'
import type { AssistantProfile } from '@/api/chat-types'

const router = useRouter()
const auth = useAuthStore()
const userId = computed(() => auth.email || 'local-user')
const assistants = ref<AssistantProfile[]>([])
const selectedId = ref('')
const busy = ref(false)
const error = ref('')
const memoryText = ref('')
const memoryUpdatedAt = ref<string | null>(null)
const memoryBusy = ref('')
const form = ref({
  name: '',
  system_prompt: '',
  capability_ids: [] as string[],
  avatar_data_url: null as string | null,
  include_runtime_context: true,
  memory_enabled: false,
  memory_update_interval: 12,
  history_search_enabled: false,
  history_similarity_threshold: 0.58,
  history_result_limit: 3,
  context_strategy: 'window' as 'window' | 'compression',
  compression_threshold_turns: 12,
  compression_threshold_tokens: 8000,
  compression_keep_recent_turns: 4,
})
const selected = computed(
  () => assistants.value.find((assistant) => assistant.id === selectedId.value) || null,
)
const isDefault = computed(() => Boolean(selected.value?.is_default))

function resetForm() {
  selectedId.value = ''
  form.value = {
    name: '',
    system_prompt: '',
    capability_ids: [],
    avatar_data_url: null,
    include_runtime_context: true,
    memory_enabled: false,
    memory_update_interval: 12,
    history_search_enabled: false,
    history_similarity_threshold: 0.58,
    history_result_limit: 3,
    context_strategy: 'window',
    compression_threshold_turns: 12,
    compression_threshold_tokens: 8000,
    compression_keep_recent_turns: 4,
  }
  memoryText.value = ''
  memoryUpdatedAt.value = null
}
function edit(assistant: AssistantProfile) {
  selectedId.value = assistant.id
  form.value = {
    name: assistant.name,
    system_prompt: assistant.system_prompt,
    capability_ids: [...assistant.capability_ids],
    avatar_data_url: assistant.avatar_data_url || null,
    include_runtime_context: assistant.include_runtime_context,
    memory_enabled: assistant.memory_enabled,
    memory_update_interval: assistant.memory_update_interval,
    history_search_enabled: assistant.history_search_enabled,
    history_similarity_threshold: assistant.history_similarity_threshold,
    history_result_limit: assistant.history_result_limit,
    context_strategy: assistant.context_strategy,
    compression_threshold_turns: assistant.compression_threshold_turns,
    compression_threshold_tokens: assistant.compression_threshold_tokens,
    compression_keep_recent_turns: assistant.compression_keep_recent_turns,
  }
  void loadMemory(assistant.id)
}
async function load() {
  assistants.value = await api.listAssistants(userId.value)
}
async function save() {
  if (!form.value.name.trim()) return
  busy.value = true
  error.value = ''
  try {
    const payload = { ...form.value, name: form.value.name.trim(), user_id: userId.value }
    const policy = {
      memory_enabled: form.value.memory_enabled,
      memory_update_interval: form.value.memory_update_interval,
      history_search_enabled: form.value.history_search_enabled,
      history_similarity_threshold: form.value.history_similarity_threshold,
      history_result_limit: form.value.history_result_limit,
      context_strategy: form.value.context_strategy,
      compression_threshold_turns: form.value.compression_threshold_turns,
      compression_threshold_tokens: form.value.compression_threshold_tokens,
      compression_keep_recent_turns: form.value.compression_keep_recent_turns,
    }
    if (selectedId.value)
      await api.updateAssistant(selectedId.value, userId.value, isDefault.value ? policy : payload)
    else await api.createAssistant(payload)
    const savedId = selectedId.value
    await load()
    const saved = assistants.value.find((item) => item.id === savedId)
    if (saved) edit(saved)
    else resetForm()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '保存失败'
  } finally {
    busy.value = false
  }
}
async function loadMemory(assistantId: string) {
  try {
    const memory = await api.getAssistantMemory(assistantId, userId.value)
    if (selectedId.value !== assistantId) return
    memoryText.value = memory.summary
    memoryUpdatedAt.value = memory.updated_at || null
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '记忆加载失败'
  }
}
async function saveMemory() {
  if (!selectedId.value) return
  memoryBusy.value = 'save'
  try {
    const memory = await api.saveAssistantMemory(selectedId.value, userId.value, memoryText.value)
    memoryUpdatedAt.value = memory.updated_at || null
  } finally { memoryBusy.value = '' }
}
async function refreshMemory() {
  if (!selectedId.value) return
  memoryBusy.value = 'refresh'
  try {
    const memory = await api.refreshAssistantMemory(selectedId.value, userId.value)
    memoryText.value = memory.summary
    memoryUpdatedAt.value = memory.updated_at || null
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '记忆更新失败' }
  finally { memoryBusy.value = '' }
}
async function clearMemory() {
  if (!selectedId.value) return
  memoryBusy.value = 'clear'
  try {
    await api.clearAssistantMemory(selectedId.value, userId.value)
    memoryText.value = ''
    memoryUpdatedAt.value = null
  } finally { memoryBusy.value = '' }
}
async function remove(assistant: AssistantProfile) {
  if (assistant.is_default) return
  try {
    await api.deleteAssistant(assistant.id, userId.value)
    await load()
    if (selectedId.value === assistant.id) resetForm()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '删除失败'
  }
}
async function uploadAvatar(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/') || file.size > 1_400_000) {
    error.value = '请选择 1.4 MB 以内的图片'
    return
  }
  form.value.avatar_data_url = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
onMounted(() => {
  void load()
})
</script>

<template>
  <main class="assistants-page">
    <header>
      <button @click="router.push('/chat')">← 返回工作台</button>
      <p>AGENT STUDIO / 02</p>
      <h1>为任务，<em>选择一个思考者。</em></h1>
      <span>每个助手拥有独立会话列表、提示词与已挂载能力。</span>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <section class="workspace">
      <aside class="assistant-list">
        <div class="list-head">
          <h2>助手</h2>
          <button @click="resetForm">＋ 新建</button>
        </div>
        <button
          v-for="assistant in assistants"
          :key="assistant.id"
          class="assistant-card"
          :class="{ selected: assistant.id === selectedId }"
          @click="edit(assistant)"
        >
          <img v-if="assistant.avatar_data_url" :src="assistant.avatar_data_url" alt="" /><span
            v-else
            >{{ assistant.name.slice(0, 2).toUpperCase() }}</span
          ><i>{{ assistant.is_default ? 'DEFAULT' : 'CUSTOM' }}</i
          ><strong>{{ assistant.name }}</strong
          ><small>{{ assistant.capability_ids.length }} 个已挂载能力</small>
        </button>
      </aside>
      <form class="editor" @submit.prevent="save">
        <div class="editor-head">
          <div>
            <p>{{ selectedId ? (isDefault ? '默认助手' : '编辑助手') : '新建助手' }}</p>
            <h2>{{ selectedId ? form.name : '配置一个新助手' }}</h2>
          </div>
          <button
            v-if="selected && !selected.is_default"
            type="button"
            class="danger"
            @click="remove(selected)"
          >
            删除
          </button>
        </div>
        <div v-if="isDefault" class="default-note">
          默认助手始终挂载全部基础能力，提示词保持内置；记忆与上下文策略仍可独立调整。
        </div>
        <template v-else>
          <label>名称<input v-model="form.name" maxlength="80" placeholder="例如：项目策划师" /></label>
          <label>系统提示词<textarea v-model="form.system_prompt" rows="8" placeholder="定义这个助手的角色、边界与工作方式…" /></label>
          <fieldset>
            <legend>挂载能力</legend>
            <label class="check"><input v-model="form.capability_ids" type="checkbox" value="agent.email" />邮件子代理<small>撰写邮件、查询联系人并发送</small></label>
            <label class="check"><input v-model="form.capability_ids" type="checkbox" value="agent.music" />音乐子代理<small>网易云搜索、每日推荐与可播放卡片</small></label>
          </fieldset>
          <label class="check"><input v-model="form.include_runtime_context" type="checkbox" />注入运行时环境<small>向最新用户请求附加时间、时区、语言和用户名</small></label>
          <div class="avatar-field">
            <p>头像</p>
            <label class="avatar-upload-card">
              <input class="avatar-file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="uploadAvatar" />
              <img v-if="form.avatar_data_url" :src="form.avatar_data_url" alt="" />
              <span v-else class="avatar-placeholder">{{ form.name.trim().slice(0, 2).toUpperCase() || 'AI' }}</span>
              <span class="avatar-upload-copy"><strong>{{ form.avatar_data_url ? '更换头像' : '选择头像' }}</strong><small>PNG、JPG、WebP 或 GIF · 最大 1.4 MB</small></span>
              <i aria-hidden="true">↗</i>
            </label>
            <button v-if="form.avatar_data_url" class="remove-avatar" type="button" @click="form.avatar_data_url = null">移除头像</button>
          </div>
        </template>

        <section class="policy-studio">
          <div class="policy-title"><span>CONTEXT ENGINE</span><h3>记忆与上下文</h3><i>按助手生效</i></div>
          <div class="policy-grid">
            <label class="policy-switch"><input v-model="form.memory_enabled" type="checkbox" /><span><b>跨会话记忆</b><small>定期提炼稳定偏好与长期事实</small></span></label>
            <label class="policy-switch"><input v-model="form.history_search_enabled" type="checkbox" /><span><b>历史语义检索</b><small>由主模型判断是否调用，不强制逐轮搜索</small></span></label>
          </div>
          <div v-if="form.memory_enabled" class="number-strip">
            <label>记忆更新间隔<input v-model.number="form.memory_update_interval" type="number" min="2" max="100" /><span>轮</span></label>
          </div>
          <div v-if="form.history_search_enabled" class="tuning-grid">
            <label>相似度阈值 <output>{{ form.history_similarity_threshold.toFixed(2) }}</output><input v-model.number="form.history_similarity_threshold" type="range" min="0" max="0.95" step="0.01" /></label>
            <label>最多返回<input v-model.number="form.history_result_limit" type="number" min="1" max="10" /><span>条</span></label>
          </div>

          <div class="strategy-head"><div><b>上下文策略</b><small>原始消息始终保留，只改变发给模型的内容</small></div><div class="strategy-tabs"><label :class="{ active: form.context_strategy === 'window' }"><input v-model="form.context_strategy" type="radio" value="window" />滚动窗口</label><label :class="{ active: form.context_strategy === 'compression' }"><input v-model="form.context_strategy" type="radio" value="compression" />总结压缩</label></div></div>
          <div v-if="form.context_strategy === 'compression'" class="compression-grid">
            <label>触发轮次<input v-model.number="form.compression_threshold_turns" type="number" min="4" max="200" /></label>
            <label>触发 Token<input v-model.number="form.compression_threshold_tokens" type="number" min="1000" max="500000" step="1000" /></label>
            <label>保留最新轮次<input v-model.number="form.compression_keep_recent_turns" type="number" min="1" max="32" /></label>
          </div>

          <div v-if="selectedId" class="memory-ledger">
            <div><b>当前核心记忆</b><small>{{ memoryUpdatedAt ? `更新于 ${new Date(memoryUpdatedAt).toLocaleString()}` : '尚未形成记忆' }}</small></div>
            <textarea v-model="memoryText" rows="7" placeholder="这里会保存跨会话稳定记忆，也可由你直接编辑。" />
            <div class="memory-actions"><button type="button" :disabled="Boolean(memoryBusy)" @click="saveMemory">保存文本</button><button type="button" :disabled="Boolean(memoryBusy) || !form.memory_enabled" @click="refreshMemory">{{ memoryBusy === 'refresh' ? '提炼中…' : '立即提炼' }}</button><button type="button" class="memory-clear" :disabled="Boolean(memoryBusy) || !memoryText" @click="clearMemory">清空</button></div>
          </div>
        </section>

        <button class="save" :disabled="busy || !form.name.trim()">{{ busy ? '保存中…' : '保存助手与策略 →' }}</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.assistants-page {
  min-height: 100vh;
  background: #141414;
  color: #eeece6;
  padding: 44px clamp(22px, 8vw, 120px);
  font-family: Manrope, sans-serif;
}
.assistants-page header {
  max-width: 760px;
  margin-bottom: 48px;
}
.assistants-page header > button {
  border: 0;
  background: transparent;
  color: #aaa;
  padding: 0;
  margin-bottom: 42px;
  font: 11px 'DM Mono';
  cursor: pointer;
}
.assistants-page header p {
  color: #d9ff36;
  font: 10px 'DM Mono';
  letter-spacing: 0.16em;
}
.assistants-page h1 {
  font: 600 clamp(44px, 7vw, 84px)/0.95 'Playfair Display';
  letter-spacing: -0.06em;
  margin: 13px 0;
}
.assistants-page h1 em {
  color: #85827b;
}
.assistants-page header > span {
  color: #aaa69d;
  font-size: 13px;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(240px, 0.7fr) minmax(0, 1.4fr);
  gap: 56px;
  max-width: 1120px;
}
.list-head,
.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #454545;
  padding-bottom: 12px;
}
.list-head h2,
.editor h2 {
  margin: 0;
  font-size: 15px;
}
.list-head button,
.danger {
  border: 1px solid #555;
  background: transparent;
  color: #d9ff36;
  padding: 7px 9px;
  font: 10px 'DM Mono';
  cursor: pointer;
}
.assistant-card {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 2px 10px;
  align-items: center;
  border: 1px solid transparent;
  border-bottom-color: #333;
  background: transparent;
  color: #d7d4cd;
  padding: 14px 8px;
  text-align: left;
  cursor: pointer;
}
.assistant-card:hover,
.assistant-card.selected {
  background: #222;
  border-color: #575757;
}
.assistant-card img,
.assistant-card > span {
  grid-row: 1/3;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  object-fit: cover;
  background: #d9ff36;
  color: #111;
  display: grid;
  place-items: center;
  font: 10px 'DM Mono';
}
.assistant-card strong {
  font-size: 12px;
}
.assistant-card small {
  color: #85817a;
  font: 9px 'DM Mono';
}
.assistant-card i {
  position: absolute;
  right: 7px;
  top: 9px;
  color: #777;
  font: 8px 'DM Mono';
  font-style: normal;
}
.editor {
  background: #eeece6;
  color: #171717;
  padding: 30px;
  box-shadow: 10px 10px 0 #d9ff36;
}
.editor-head p {
  margin: 0 0 5px;
  color: #777;
  font: 9px 'DM Mono';
  letter-spacing: 0.12em;
}
.editor label {
  display: grid;
  gap: 7px;
  margin-top: 20px;
  font: 10px 'DM Mono';
  letter-spacing: 0.08em;
}
.editor input:not([type='checkbox']),
.editor textarea {
  width: 100%;
  box-sizing: border-box;
  border: 0;
  border-bottom: 1px solid #aaa79e;
  background: transparent;
  padding: 9px 0;
  outline: 0;
  font: 13px/1.6 Manrope;
}
.editor textarea {
  resize: vertical;
  border: 1px solid #aaa79e;
  padding: 9px;
}
.editor fieldset {
  margin: 24px 0 0;
  padding: 12px;
  border: 1px solid #aaa79e;
}
.editor legend {
  font: 10px 'DM Mono';
  letter-spacing: 0.08em;
}
.editor .check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  font: 11px Manrope;
  letter-spacing: 0;
}
.check input {
  margin: 2px 0;
}
.check small {
  display: block;
  color: #777;
  font: 9px/1.5 'DM Mono';
}
.default-note {
  margin-top: 24px;
  padding: 18px;
  border-left: 3px solid #d9ff36;
  background: #ddd9d0;
  font: 12px/1.7 Manrope;
}
.avatar-field {
  margin-top: 19px;
}
.avatar-field > p {
  margin: 0 0 8px;
  color: #5d5a52;
  font: 10px 'DM Mono';
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.avatar-upload-card {
  position: relative;
  display: grid !important;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  margin: 0 !important;
  padding: 10px 12px !important;
  overflow: hidden;
  border: 1px dashed #98938a;
  background: #f6f4ee;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}
.avatar-upload-card::before {
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 42%, rgb(217 255 54 / 0.16));
  content: '';
  opacity: 0;
  transition: opacity 160ms ease;
}
.avatar-upload-card:hover {
  border-color: #171717;
  border-style: solid;
  box-shadow: 4px 4px 0 #d9ff36;
  transform: translate(-1px, -1px);
}
.avatar-upload-card:hover::before {
  opacity: 1;
}
.avatar-file {
  position: absolute;
  z-index: 3;
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  opacity: 0;
}
.avatar-upload-card img,
.avatar-placeholder {
  position: relative;
  z-index: 1;
  width: 46px;
  height: 46px;
  border: 1px solid #171717;
  border-radius: 10px;
  object-fit: cover;
}
.avatar-placeholder {
  display: grid;
  place-items: center;
  background: #171717;
  color: #d9ff36;
  font: 700 12px 'DM Mono';
  letter-spacing: -0.05em;
}
.avatar-upload-copy {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 3px;
  min-width: 0;
}
.avatar-upload-copy strong {
  color: #171717;
  font: 700 12px Manrope;
}
.avatar-upload-copy small {
  overflow: hidden;
  color: #77736a;
  font: 9px 'DM Mono';
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.avatar-upload-card i {
  position: relative;
  z-index: 1;
  color: #171717;
  font: 20px/1 'DM Mono';
  font-style: normal;
}
.remove-avatar {
  margin-top: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #77736a;
  font: 10px 'DM Mono';
  cursor: pointer;
}
.remove-avatar:hover {
  color: #a43321;
  text-decoration: line-through;
}
.save {
  margin-top: 28px;
  border: 0;
  background: #171717;
  color: #fff;
  padding: 12px 16px;
  font: 700 12px Manrope;
  cursor: pointer;
}
.editor fieldset {
  border: 0;
  background: #e0ddd5;
  padding: 14px 15px;
  margin-top: 24px;
}
.editor fieldset legend {
  padding: 0;
  color: #6e6b64;
}
.editor .check {
  position: relative;
  min-height: 48px;
  display: block;
  margin-top: 14px !important;
  padding: 12px 56px 12px 13px;
  border: 1px solid #b8b4ab;
  background: #f5f3ed;
  color: #1b1b19;
  font: 600 12px Manrope !important;
  letter-spacing: 0 !important;
  cursor: pointer;
  transition: 0.18s;
}
.editor .check:hover {
  border-color: #171717;
  box-shadow: 3px 3px 0 #d9ff36;
}
.editor .check input {
  appearance: none;
  position: absolute;
  right: 12px;
  top: 50%;
  width: 34px;
  height: 18px;
  margin: 0;
  transform: translateY(-50%);
  border-radius: 999px;
  background: #aaa69d;
  cursor: pointer;
  transition: 0.2s;
}
.editor .check input:after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  transition: 0.2s;
}
.editor .check input:checked {
  background: #171717;
}
.editor .check input:checked:after {
  left: 19px;
  background: #d9ff36;
}
.editor .check small {
  display: block;
  margin-top: 5px;
  color: #706d66;
  font: 9px/1.5 'DM Mono';
}
.editor > template + .check {
  margin-top: 18px !important;
  background: #ece9e1;
}
.error {
  color: #ff7a70;
  font: 11px 'DM Mono';
}
@media (max-width: 760px) {
  .assistants-page {
    padding: 28px 20px;
  }
  .workspace {
    grid-template-columns: 1fr;
    gap: 35px;
  }
}
.policy-studio{margin-top:30px;padding-top:24px;border-top:2px solid #171717}.policy-title{display:grid;grid-template-columns:1fr auto;align-items:end;margin-bottom:15px}.policy-title span{grid-column:1/-1;color:#747168;font:8px 'DM Mono';letter-spacing:.16em}.policy-title h3{margin:5px 0 0;font:700 19px Manrope;letter-spacing:-.04em}.policy-title i{color:#77736a;font:8px 'DM Mono';font-style:normal}.policy-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.editor .policy-switch{position:relative;display:grid;grid-template-columns:34px 1fr;gap:10px;align-items:center;margin:0;padding:13px;border:1px solid #b8b4ab;background:#f7f5ef;cursor:pointer}.policy-switch>input{appearance:none;width:28px;height:28px;margin:0;border:1px solid #171717;background:#e1ded6}.policy-switch>input:checked{background:#171717;box-shadow:inset 0 0 0 7px #d9ff36}.policy-switch span{display:grid;gap:3px}.policy-switch b{font:700 11px Manrope}.policy-switch small{color:#747067;font:8px/1.45 'DM Mono'}.number-strip,.tuning-grid,.compression-grid{display:grid;gap:8px;margin-top:8px}.tuning-grid{grid-template-columns:1.5fr .7fr}.compression-grid{grid-template-columns:repeat(3,1fr)}.number-strip label,.tuning-grid label,.compression-grid label{position:relative;margin:0;padding:11px 12px;border:1px solid #c4c0b7;background:#e6e3db;color:#5f5b53;font:8px 'DM Mono'}.number-strip input,.tuning-grid input[type=number],.compression-grid input{border:0!important;border-bottom:1px solid #8b877e!important;background:transparent!important;padding:6px 22px 3px 0!important;font:700 13px 'DM Mono'!important}.number-strip span,.tuning-grid label>span{position:absolute;right:13px;bottom:15px;color:#6d6961}.tuning-grid output{float:right;color:#171717;font-weight:700}.tuning-grid input[type=range]{width:100%;accent-color:#171717}.strategy-head{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-top:22px;padding-top:17px;border-top:1px solid #b8b4ab}.strategy-head>div:first-child{display:grid;gap:4px}.strategy-head b{font:700 11px Manrope}.strategy-head small{color:#757168;font:8px 'DM Mono'}.strategy-tabs{display:flex;border:1px solid #171717}.editor .strategy-tabs label{display:block;margin:0;padding:7px 10px;color:#514e48;font:8px 'DM Mono';cursor:pointer}.strategy-tabs label.active{background:#171717;color:#d9ff36}.strategy-tabs input{display:none}.memory-ledger{margin-top:22px;padding:15px;background:#171717;color:#efede6;box-shadow:5px 5px 0 #d9ff36}.memory-ledger>div:first-child{display:flex;justify-content:space-between;align-items:center}.memory-ledger b{font:700 11px Manrope}.memory-ledger small{color:#817e76;font:8px 'DM Mono'}.editor .memory-ledger textarea{margin-top:12px;border:1px solid #444;background:#202020;color:#e6e3dc;font:11px/1.7 'DM Mono';resize:vertical}.memory-actions{display:flex;gap:7px;margin-top:9px}.memory-actions button{border:1px solid #555;background:transparent;color:#d9ff36;padding:7px 9px;font:8px 'DM Mono';cursor:pointer}.memory-actions button:disabled{opacity:.35;cursor:not-allowed}.memory-actions .memory-clear{margin-left:auto;border-color:transparent;color:#8d8980}@media(max-width:760px){.policy-grid,.tuning-grid,.compression-grid{grid-template-columns:1fr}.strategy-head{align-items:flex-start;flex-direction:column}.memory-ledger>div:first-child{align-items:flex-start;flex-direction:column;gap:5px}}
</style>
