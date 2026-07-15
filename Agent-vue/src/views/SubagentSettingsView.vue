<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as settingsApi from '@/api/subagent-settings'
import type { SubagentSettings } from '@/api/chat-types'

const router = useRouter()
const auth = useAuthStore()
const userId = computed(() => auth.email || 'local-user')
const settings = ref<SubagentSettings[]>([])
const loading = ref(true)
const saving = ref('')
const saved = ref('')
const error = ref('')

const moduleIndex: Record<string, string> = {
  'agent.email': 'MAIL',
  'agent.music': 'NCM',
  'agent.bilibili': 'BILI',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    settings.value = await settingsApi.listSubagentSettings(userId.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '子代理配置加载失败'
  } finally {
    loading.value = false
  }
}

async function save(item: SubagentSettings) {
  saving.value = item.capability_id
  saved.value = ''
  error.value = ''
  try {
    const updated = await settingsApi.saveSubagentSettings(
      userId.value,
      item.capability_id,
      item.config,
    )
    const index = settings.value.findIndex((entry) => entry.capability_id === item.capability_id)
    if (index >= 0) settings.value[index] = updated
    saved.value = item.capability_id
    window.setTimeout(() => {
      if (saved.value === item.capability_id) saved.value = ''
    }, 1600)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '保存失败'
  } finally {
    saving.value = ''
  }
}

onMounted(load)
</script>

<template>
  <main class="agent-settings">
    <header class="page-head">
      <button class="back" @click="router.push('/chat')">← 返回工作台</button>
      <nav class="settings-nav" aria-label="配置模块">
        <button @click="router.push('/settings/models')">模型路由</button>
        <button class="active">子代理</button>
      </nav>
      <p>SUBAGENT SYSTEMS / 02</p>
      <h1>能力各自运行，<em>配置全局复用。</em></h1>
      <span>所有助手共享同一套用户级子代理参数；每个能力模块独立保存，互不串值。</span>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="loading" class="loading-grid" aria-label="正在加载子代理配置">
      <i v-for="index in 3" :key="index"></i>
    </section>
    <section v-else class="module-grid">
      <article
        v-for="(item, index) in settings"
        :key="item.capability_id"
        class="module-card"
        :class="{ dormant: !item.fields.length }"
      >
        <div class="module-head">
          <span class="module-code">{{ moduleIndex[item.capability_id] || 'AGT' }}</span>
          <small>{{ String(index + 1).padStart(2, '0') }}</small>
        </div>
        <div class="module-copy">
          <p>{{ item.capability_id }}</p>
          <h2>{{ item.display_name }}</h2>
          <span>{{ item.description }}</span>
        </div>

        <div v-if="item.fields.length" class="field-list">
          <label v-for="field in item.fields" :key="field.key">
            <span><strong>{{ field.label }}</strong><small>{{ field.description }}</small></span>
            <input
              v-if="field.type === 'number'"
              v-model.number="item.config[field.key]"
              type="number"
              :min="field.minimum ?? undefined"
              :max="field.maximum ?? undefined"
            />
            <input v-else-if="field.type === 'boolean'" v-model="item.config[field.key]" type="checkbox" />
            <input v-else v-model="item.config[field.key]" type="text" />
          </label>
        </div>
        <p v-else class="no-fields">当前模块没有需要调整的运行参数。</p>

        <footer>
          <span><i></i> USER GLOBAL</span>
          <button
            v-if="item.fields.length"
            :disabled="saving === item.capability_id"
            @click="save(item)"
          >
            {{ saving === item.capability_id ? '保存中…' : saved === item.capability_id ? '已保存 ✓' : '保存此模块 →' }}
          </button>
        </footer>
      </article>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.agent-settings{min-height:100vh;background:#141414;color:#eeece6;padding:44px clamp(22px,8vw,120px) 90px;font-family:Manrope,sans-serif}.page-head{position:relative;max-width:1040px;margin-bottom:52px}.back{border:0;background:transparent;color:#aaa69d;padding:0;margin-bottom:50px;font:11px 'DM Mono';cursor:pointer}.back:hover{color:#d9ff36}.settings-nav{position:absolute;right:0;top:0;display:flex;border:1px solid #393939;padding:3px}.settings-nav button{border:0;background:transparent;color:#74716b;padding:8px 14px;font:9px 'DM Mono';letter-spacing:.08em;cursor:pointer}.settings-nav button:hover{color:#eeece6}.settings-nav .active{background:#d9ff36;color:#111}.page-head>p{color:#d9ff36;font:10px 'DM Mono';letter-spacing:.16em}.page-head h1{max-width:900px;margin:13px 0;font:600 clamp(44px,6vw,78px)/.98 'Playfair Display';letter-spacing:-.055em}.page-head h1 em{color:#8d8b83}.page-head>span{display:block;max-width:640px;color:#aaa69d;font-size:13px;margin-top:22px}.module-grid{display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:1px;max-width:1120px;background:#3a3a3a;border:1px solid #3a3a3a}.module-card{position:relative;display:flex;flex-direction:column;min-height:410px;padding:25px;background:#191919;overflow:hidden}.module-card:nth-child(3n+2){background:#1c1c1c}.module-head{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:start}.module-code{display:grid;place-items:center;min-width:46px;height:28px;padding:0 8px;background:#d9ff36;color:#111;font:700 8px 'DM Mono';letter-spacing:.1em}.module-head small{color:#57544f;font:9px 'DM Mono'}.module-copy{position:relative;z-index:1;margin:28px 0 18px}.module-copy p{margin:0 0 8px;color:#6c6963;font:8px 'DM Mono';letter-spacing:.1em}.module-copy h2{margin:0 0 9px;font-size:20px;letter-spacing:-.03em}.module-copy span{display:block;max-width:420px;color:#918e86;font-size:11px;line-height:1.6}.field-list{position:relative;z-index:1;border-top:1px solid #333}.field-list label{display:grid;grid-template-columns:minmax(0,1fr) 68px;gap:24px;align-items:center;padding:17px 0;border-bottom:1px solid #2d2d2d}.field-list label>span{display:grid;gap:5px}.field-list strong{font-size:11px}.field-list small{color:#74716b;font:8px/1.45 'DM Mono'}.field-list input[type=number],.field-list input[type=text]{width:68px;box-sizing:border-box;border:1px solid #484848;background:#121212;color:#d9ff36;padding:9px 7px;text-align:center;outline:0;font:11px 'DM Mono'}.field-list input:focus{border-color:#d9ff36}.no-fields{margin:auto 0;color:#66635e;font:9px 'DM Mono'}.module-card footer{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:24px}.module-card footer>span{display:flex;align-items:center;gap:7px;color:#68655f;font:8px 'DM Mono';letter-spacing:.1em}.module-card footer>span i{width:5px;height:5px;border-radius:50%;background:#d9ff36;box-shadow:0 0 8px #d9ff36}.module-card footer button{border:1px solid #515151;background:transparent;color:#d9ff36;padding:9px 12px;font:8px 'DM Mono';cursor:pointer}.module-card footer button:hover{border-color:#d9ff36;background:#d9ff36;color:#111}.module-card footer button:disabled{opacity:.45;cursor:wait}.error{max-width:1120px;color:#ff796f;font:10px 'DM Mono';margin:-20px 0 24px}.loading-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;max-width:1120px}.loading-grid i{height:410px;background:linear-gradient(100deg,#191919 20%,#242424 50%,#191919 80%);background-size:200% 100%;animation:scan 1.3s linear infinite}@keyframes scan{to{background-position:-200% 0}}@media(max-width:760px){.agent-settings{padding:27px 20px 60px}.back{margin-bottom:75px}.settings-nav{left:0;right:auto;top:42px}.module-grid,.loading-grid{grid-template-columns:1fr}.module-card{min-height:380px}}
</style>
