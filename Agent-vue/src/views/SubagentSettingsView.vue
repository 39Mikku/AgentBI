<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as settingsApi from '@/api/capability-settings'
import type { CapabilitySettings } from '@/api/chat-types'
import * as imageGenerationApi from '@/api/image-generation'
import type { CodexImageOAuthStart, CodexImageOAuthStatus } from '@/api/image-generation-types'

const router = useRouter()
const auth = useAuthStore()
const userId = computed(() => auth.email || 'local-user')
const settings = ref<CapabilitySettings[]>([])
const loading = ref(true)
const saving = ref('')
const saved = ref('')
const error = ref('')
const codexStatus = ref<CodexImageOAuthStatus | null>(null)
const codexLogin = ref<CodexImageOAuthStart | null>(null)
const oauthBusy = ref(false)
let oauthPoll: ReturnType<typeof setInterval> | null = null

const moduleIndex: Record<string, string> = {
  'agent.email': 'MAIL',
  'agent.music': 'NCM',
  'agent.bilibili': 'BILI',
  'tool.web_search': 'WEB',
  'tool.image_generation': 'IMG',
}
const capabilityGroups = computed(() => [
  {
    kind: 'tool',
    eyebrow: 'DIRECT TOOLS',
    title: '直接工具',
    detail: '由主模型按需调用，结果回到当前推理循环。',
    items: settings.value.filter((item) => item.kind === 'tool'),
  },
  {
    kind: 'subagent',
    eyebrow: 'SUBAGENTS',
    title: '子代理',
    detail: '拥有独立工具循环，处理边界清晰的专项任务。',
    items: settings.value.filter((item) => item.kind === 'subagent'),
  },
].filter((group) => group.items.length))

async function load() {
  loading.value = true
  error.value = ''
  try {
    settings.value = await settingsApi.listCapabilitySettings(userId.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '子代理配置加载失败'
  } finally {
    loading.value = false
  }
}

async function save(item: CapabilitySettings) {
  saving.value = item.capability_id
  saved.value = ''
  error.value = ''
  try {
    const updated = await settingsApi.saveCapabilitySettings(
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

async function loadCodexStatus() {
  codexStatus.value = await imageGenerationApi.getCodexImageStatus()
  if (codexStatus.value.connected) {
    codexLogin.value = null
    if (oauthPoll) clearInterval(oauthPoll)
    oauthPoll = null
  }
}

async function connectCodex() {
  oauthBusy.value = true
  error.value = ''
  try {
    codexLogin.value = await imageGenerationApi.connectCodexImage()
    window.open(codexLogin.value.authorization_url, '_blank', 'noopener,noreferrer')
    await loadCodexStatus()
    if (oauthPoll) clearInterval(oauthPoll)
    oauthPoll = setInterval(() => void loadCodexStatus().catch(() => undefined), 2000)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Codex 连接启动失败'
  } finally {
    oauthBusy.value = false
  }
}

async function disconnectCodex() {
  oauthBusy.value = true
  try {
    await imageGenerationApi.disconnectCodexImage()
    codexLogin.value = null
    await loadCodexStatus()
  } finally {
    oauthBusy.value = false
  }
}

async function copyDeviceCode() {
  if (codexLogin.value?.user_code) await navigator.clipboard.writeText(codexLogin.value.user_code)
}

onMounted(async () => {
  await Promise.all([load(), loadCodexStatus()])
})
onBeforeUnmount(() => {
  if (oauthPoll) clearInterval(oauthPoll)
})
</script>

<template>
  <main class="agent-settings">
    <header class="page-head">
      <button class="back" @click="router.push('/chat')">← 返回工作台</button>
      <nav class="settings-nav" aria-label="配置模块">
        <button @click="router.push('/settings/models')">模型路由</button>
        <button class="active">能力</button>
      </nav>
      <p>CAPABILITY SYSTEMS / 02</p>
      <h1>能力各自运行，<em>配置全局复用。</em></h1>
      <span>直接工具与子代理统一挂载、分组配置；每个能力模块独立保存，互不串值。</span>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="loading" class="loading-grid" aria-label="正在加载能力配置">
      <i v-for="index in 3" :key="index"></i>
    </section>
    <template v-else><section v-for="group in capabilityGroups" :key="group.kind" class="capability-group">
      <header class="group-head">
        <div><p>{{ group.eyebrow }}</p><h2>{{ group.title }}</h2></div>
        <span>{{ group.detail }}</span>
      </header>
      <div class="module-grid"><article
        v-for="(item, index) in group.items"
        :key="item.capability_id"
        class="module-card"
        :class="{ dormant: !item.fields.length, image: item.capability_id === 'tool.image_generation' }"
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
          <label
            v-for="field in item.fields"
            v-show="
              item.capability_id !== 'tool.image_generation' ||
              field.key === 'mode' ||
              (field.key === 'lite_model' && item.config.mode === 'lite') ||
              (field.key === 'pro_quality' && item.config.mode === 'pro')
            "
            :key="field.key"
          >
            <span><strong>{{ field.label }}</strong><small>{{ field.description }}</small></span>
            <input
              v-if="field.type === 'number'"
              v-model.number="item.config[field.key]"
              type="number"
              :min="field.minimum ?? undefined"
              :max="field.maximum ?? undefined"
            />
            <select v-else-if="field.type === 'select'" v-model="item.config[field.key]">
              <option v-for="option in field.options || []" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
            <input v-else-if="field.type === 'boolean'" v-model="item.config[field.key]" type="checkbox" />
            <input v-else v-model="item.config[field.key]" type="text" />
          </label>
        </div>
        <section v-if="item.capability_id === 'tool.image_generation'" class="oauth-console">
          <header>
            <span><i :class="{ connected: codexStatus?.connected, pending: codexStatus?.pending }"></i> CODEX OAUTH</span>
            <b>{{ codexStatus?.connected ? 'CONNECTED' : codexStatus?.pending ? 'WAITING' : 'OFFLINE' }}</b>
          </header>
          <p v-if="codexStatus?.connected">独立会话已连接<span v-if="codexStatus.account_id"> · {{ codexStatus.account_id }}</span></p>
          <div v-else-if="codexLogin" class="device-code">
            <span>在新窗口登录后输入设备码</span>
            <button type="button" @click="copyDeviceCode">{{ codexLogin.user_code }} <small>复制</small></button>
          </div>
          <p v-else>凭据单独保存在本项目本地文件，不占用或覆盖 Codex IDE / CLI 登录。</p>
          <p v-if="codexStatus?.error" class="oauth-error">{{ codexStatus.error }}</p>
          <button v-if="codexStatus?.connected" type="button" :disabled="oauthBusy" @click="disconnectCodex">断开连接</button>
          <button v-else type="button" :disabled="oauthBusy || codexStatus?.pending" @click="connectCodex">{{ codexStatus?.pending ? '等待浏览器确认…' : '连接 Codex ↗' }}</button>
        </section>
        <p v-if="!item.fields.length" class="no-fields">当前模块没有需要调整的运行参数。</p>

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
      </article></div>
    </section></template>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.agent-settings{min-height:100vh;background:#141414;color:#eeece6;padding:44px clamp(22px,8vw,120px) 90px;font-family:Manrope,sans-serif}.page-head{position:relative;max-width:1040px;margin-bottom:52px}.back{border:0;background:transparent;color:#aaa69d;padding:0;margin-bottom:50px;font:11px 'DM Mono';cursor:pointer}.back:hover{color:#d9ff36}.settings-nav{position:absolute;right:0;top:0;display:flex;border:1px solid #393939;padding:3px}.settings-nav button{border:0;background:transparent;color:#74716b;padding:8px 14px;font:9px 'DM Mono';letter-spacing:.08em;cursor:pointer}.settings-nav button:hover{color:#eeece6}.settings-nav .active{background:#d9ff36;color:#111}.page-head>p{color:#d9ff36;font:10px 'DM Mono';letter-spacing:.16em}.page-head h1{max-width:900px;margin:13px 0;font:600 clamp(44px,6vw,78px)/.98 'Playfair Display';letter-spacing:-.055em}.page-head h1 em{color:#8d8b83}.page-head>span{display:block;max-width:640px;color:#aaa69d;font-size:13px;margin-top:22px}.capability-group{max-width:1120px;margin:0 0 48px}.group-head{display:flex;justify-content:space-between;align-items:end;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #383838}.group-head p{margin:0 0 5px;color:#d9ff36;font:8px 'DM Mono';letter-spacing:.16em}.group-head h2{margin:0;font-size:15px}.group-head>span{max-width:430px;color:#77736d;text-align:right;font:9px/1.5 'DM Mono'}.module-grid{display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:1px;background:#3a3a3a;border:1px solid #3a3a3a}.module-card{position:relative;display:flex;flex-direction:column;min-height:410px;padding:25px;background:#191919;overflow:hidden}.module-card:nth-child(3n+2){background:#1c1c1c}.module-head{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:start}.module-code{display:grid;place-items:center;min-width:46px;height:28px;padding:0 8px;background:#d9ff36;color:#111;font:700 8px 'DM Mono';letter-spacing:.1em}.module-head small{color:#57544f;font:9px 'DM Mono'}.module-copy{position:relative;z-index:1;margin:28px 0 18px}.module-copy p{margin:0 0 8px;color:#6c6963;font:8px 'DM Mono';letter-spacing:.1em}.module-copy h2{margin:0 0 9px;font-size:20px;letter-spacing:-.03em}.module-copy span{display:block;max-width:420px;color:#918e86;font-size:11px;line-height:1.6}.field-list{position:relative;z-index:1;border-top:1px solid #333}.field-list label{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:24px;align-items:center;padding:17px 0;border-bottom:1px solid #2d2d2d}.field-list label>span{display:grid;gap:5px}.field-list strong{font-size:11px}.field-list small{color:#74716b;font:8px/1.45 'DM Mono'}.field-list input[type=number],.field-list input[type=text],.field-list select{width:92px;box-sizing:border-box;border:1px solid #484848;background:#121212;color:#d9ff36;padding:9px 7px;text-align:center;outline:0;font:10px 'DM Mono'}.field-list input:focus,.field-list select:focus{border-color:#d9ff36}.no-fields{margin:auto 0;color:#66635e;font:9px 'DM Mono'}.module-card footer{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:24px}.module-card footer>span{display:flex;align-items:center;gap:7px;color:#68655f;font:8px 'DM Mono';letter-spacing:.1em}.module-card footer>span i{width:5px;height:5px;border-radius:50%;background:#d9ff36;box-shadow:0 0 8px #d9ff36}.module-card footer button{border:1px solid #515151;background:transparent;color:#d9ff36;padding:9px 12px;font:8px 'DM Mono';cursor:pointer}.module-card footer button:hover{border-color:#d9ff36;background:#d9ff36;color:#111}.module-card footer button:disabled{opacity:.45;cursor:wait}.error{max-width:1120px;color:#ff796f;font:10px 'DM Mono';margin:-20px 0 24px}.loading-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;max-width:1120px}.loading-grid i{height:410px;background:linear-gradient(100deg,#191919 20%,#242424 50%,#191919 80%);background-size:200% 100%;animation:scan 1.3s linear infinite}@keyframes scan{to{background-position:-200% 0}}@media(max-width:760px){.agent-settings{padding:27px 20px 60px}.back{margin-bottom:75px}.settings-nav{left:0;right:auto;top:42px}.module-grid,.loading-grid{grid-template-columns:1fr}.group-head{align-items:start}.group-head>span{max-width:180px}.module-card{min-height:380px}}
.module-card.image{background:radial-gradient(circle at 92% 8%,rgba(217,255,54,.09),transparent 31%),#191919}.module-card.image .field-list input[type=text]{width:180px;text-align:left}.oauth-console{margin:16px 0 0;padding:13px;border:1px solid #333;background:#111}.oauth-console header{display:flex;justify-content:space-between;align-items:center}.oauth-console header span{display:flex;align-items:center;gap:7px;color:#aaa69d;font:8px 'DM Mono';letter-spacing:.1em}.oauth-console header i{width:6px;height:6px;border-radius:50%;background:#555}.oauth-console header i.connected{background:#d9ff36;box-shadow:0 0 9px #d9ff36}.oauth-console header i.pending{background:#ffb84c;animation:oauthPulse 1s ease-in-out infinite}.oauth-console header b{color:#69665f;font:7px 'DM Mono'}.oauth-console>p{margin:10px 0;color:#6e6a64;font:8px/1.5 'DM Mono'}.oauth-console>button{border:1px solid #4a4a4a;background:transparent;color:#d9ff36;padding:8px 10px;font:8px 'DM Mono';cursor:pointer}.device-code{display:grid;gap:7px;margin:11px 0}.device-code>span{color:#77736d;font:8px 'DM Mono'}.device-code>button{display:flex;justify-content:space-between;border:1px solid #565656;background:#191919;color:#eeece6;padding:10px 12px;font:500 13px 'DM Mono';letter-spacing:.15em;cursor:pointer}.device-code small{color:#d9ff36;font:7px 'DM Mono';letter-spacing:0}.oauth-console .oauth-error{color:#ff796f}@keyframes oauthPulse{50%{opacity:.25}}
</style>
