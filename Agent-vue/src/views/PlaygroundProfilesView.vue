<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { assetContentUrl } from '@/utils/chat-attachments'
import { useWorkspaceStore } from '@/stores/workspace'
import { usePlaygroundStore } from '@/stores/playground'
import type { PlaygroundPreferences, PlaygroundProfile, PlaygroundProfileType } from '@/api/playground-types'
import PlaygroundModelSettings from '@/components/playground/PlaygroundModelSettings.vue'
import PlaygroundProfileEditor from '@/components/playground/PlaygroundProfileEditor.vue'


const workspace = useWorkspaceStore()
const store = usePlaygroundStore()
const route = useRoute()
const router = useRouter()
const userId = computed(() => workspace.userId)
const tab = ref<'profiles' | 'model'>('profiles')
const selectedId = ref('')
const newType = ref<PlaygroundProfileType>('character')
const savingModel = ref(false)
const selected = computed(
  () => store.profiles.find((item) => item.id === selectedId.value) || null,
)

function select(profile: PlaygroundProfile) {
  selectedId.value = profile.id
  newType.value = profile.profile_type
  void router.replace({ query: { ...route.query, profile_id: profile.id } })
}

function create(profileType: PlaygroundProfileType) {
  selectedId.value = ''
  newType.value = profileType
  tab.value = 'profiles'
  void router.replace({ query: { ...route.query, profile_id: undefined } })
}

async function saved(profile: PlaygroundProfile) {
  await store.reloadProfiles(userId.value)
  const stored = store.profiles.find((item) => item.id === profile.id)
  if (stored) select(stored)
}

async function deleted(profileId: string) {
  await store.reloadProfiles(userId.value)
  if (selectedId.value === profileId) selectedId.value = store.profiles[0]?.id || ''
}

async function saveModel() {
  savingModel.value = true
  try {
    await store.persistPreferences()
  } finally {
    savingModel.value = false
  }
}

function updatePreferences(value: PlaygroundPreferences) {
  store.preferences = value
}

onMounted(async () => {
  await store.load(userId.value)
  const requested = String(route.query.profile_id || '')
  selectedId.value =
    store.profiles.find((item) => item.id === requested)?.id ||
    store.activeProfileId ||
    store.profiles[0]?.id ||
    ''
  if (selected.value) newType.value = selected.value.profile_type
})
</script>

<template>
  <main class="profiles-page">
    <div class="grain"></div>
    <header class="topbar">
      <button class="brand" @click="router.push('/playground')"><i></i><strong>AGENTBI</strong><span>/ PLAYGROUND</span></button>
      <nav><button :class="{ active: tab === 'profiles' }" @click="tab = 'profiles'">角色与世界</button><button :class="{ active: tab === 'model' }" @click="tab = 'model'">模型设置</button></nav>
      <button class="back" @click="router.push('/playground')">返回故事场 ↗</button>
    </header>

    <section class="hero">
      <div><span>ROLEPLAY SYSTEM / 04</span><h1>定义人物，<em>编排世界。</em></h1></div>
      <p>设定不会被压成一层系统提示词。人设、模块、世界书、状态栏与长会话总结各自保留边界。</p>
    </section>

    <p v-if="store.error" class="page-error">{{ store.error }}</p>
    <section v-if="tab === 'profiles'" class="workspace">
      <aside class="profile-rail">
        <header><div><span>ARCHIVE</span><strong>资料库</strong></div><div class="new-actions"><button @click="create('character')">＋ 角色</button><button @click="create('world')">＋ 世界</button></div></header>
        <div class="profile-list">
          <button v-for="(profile, index) in store.profiles" :key="profile.id" :class="{ selected: profile.id === selectedId }" @click="select(profile)">
            <span class="thumb"><img v-if="profile.avatar_attachment_id" :src="assetContentUrl(profile.avatar_attachment_id, userId)" alt="" /><i v-else></i></span>
            <small>{{ String(index + 1).padStart(2, '0') }} / {{ profile.profile_type === 'character' ? 'CHARACTER' : 'WORLD' }}</small><strong>{{ profile.name }}</strong><em>{{ profile.settings.state.enabled ? 'STATE' : 'PLAIN' }} · {{ profile.settings.summary.enabled ? 'SUMMARY' : 'WINDOW' }}</em>
          </button>
          <div v-if="!store.profiles.length" class="rail-empty"><b>00</b><span>尚无角色或世界</span><small>从右上方创建第一份资料。</small></div>
        </div>
      </aside>
      <section class="editor-shell">
        <PlaygroundProfileEditor :key="selected?.id || `new-${newType}`" :profile="selected" :user-id="userId" :initial-type="newType" :preferences="store.preferences" :templates="store.stateTemplates" @saved="saved" @deleted="deleted" />
      </section>
    </section>

    <section v-else class="model-workspace">
      <PlaygroundModelSettings :model-value="store.preferences" :saving="savingModel" @update:model-value="updatePreferences" @save="saveModel" />
    </section>
  </main>
</template>

<style scoped>
.profiles-page{--pg-acid:#d7ff3f;--pg-paper:#e8ece7;--pg-muted:#737b75;--pg-line:#333a35;position:relative;min-height:100vh;padding:0 clamp(16px,4vw,62px) 70px;background:#101310;color:var(--pg-paper);font-family:var(--font-sans);overflow-x:hidden}.grain{position:fixed;inset:0;pointer-events:none;opacity:.08;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.4'/%3E%3C/svg%3E")}.topbar{position:relative;z-index:2;height:76px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;border-bottom:1px solid var(--pg-line)}.topbar button{border:0;background:none;color:inherit;cursor:pointer}.brand{justify-self:start;display:flex;align-items:center;gap:8px;padding:0;font:8px var(--font-mono);letter-spacing:.13em}.brand i{position:relative;width:15px;height:15px;border:1px solid var(--pg-acid)}.brand i:after{content:'';position:absolute;width:5px;height:5px;right:-4px;bottom:-4px;background:var(--pg-acid)}.brand span{color:#626a64}.topbar nav{display:flex;height:100%;align-items:center}.topbar nav button{align-self:stretch;border-bottom:2px solid transparent;padding:0 17px;color:#69716b;font:8px var(--font-mono)}.topbar nav button.active{border-color:var(--pg-acid);color:var(--pg-paper)}.back{justify-self:end;color:#777f79!important;font:8px var(--font-mono)}.hero{position:relative;z-index:1;max-width:1420px;margin:54px auto 35px;display:grid;grid-template-columns:1fr minmax(250px,.38fr);align-items:end;gap:40px}.hero span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.16em}.hero h1{margin:14px 0 0;font:600 clamp(45px,6vw,82px)/.9 var(--font-display);letter-spacing:-.07em}.hero h1 em{color:#666e68;font-family:'Playfair Display',serif;font-weight:500}.hero p{margin:0;padding:0 0 5px 20px;border-left:1px solid var(--pg-acid);color:#737b75;font-size:9px;line-height:1.75}.workspace{position:relative;z-index:1;max-width:1420px;margin:auto;display:grid;grid-template-columns:285px minmax(0,1fr);border:1px solid var(--pg-line);background:#161917}.profile-rail{min-height:760px;border-right:1px solid var(--pg-line);background:#131614}.profile-rail>header{display:grid;gap:17px;padding:20px;border-bottom:1px solid var(--pg-line)}.profile-rail>header div:first-child{display:flex;justify-content:space-between;align-items:baseline}.profile-rail>header span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.14em}.profile-rail>header strong{font-size:13px}.new-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px}.new-actions button{height:34px;border:1px solid #3e4640;background:#181c19;color:#9aa29c;font:7px var(--font-mono);cursor:pointer}.new-actions button:hover{border-color:var(--pg-acid);color:var(--pg-acid)}.profile-list{display:grid}.profile-list>button{display:grid;grid-template-columns:54px 1fr;grid-template-rows:auto auto auto;column-gap:13px;min-height:84px;border:0;border-bottom:1px solid #292f2b;background:transparent;color:inherit;padding:14px;text-align:left;cursor:pointer;transition:.2s}.profile-list>button:hover,.profile-list>button.selected{background:#1b1f1c}.profile-list>button.selected{box-shadow:inset 3px 0 var(--pg-acid)}.thumb{grid-row:1/-1;position:relative;width:52px;height:52px;overflow:hidden;border:1px solid #3e4640;background:#101310}.thumb img{width:100%;height:100%;object-fit:cover}.thumb i:before,.thumb i:after{content:'';position:absolute}.thumb i:before{width:20px;height:20px;left:15px;top:9px;border:1px solid #424a44;border-radius:50%}.thumb i:after{width:32px;height:16px;left:9px;bottom:7px;border:1px solid #424a44;border-radius:20px 20px 0 0}.profile-list small{color:#59615b;font:6px var(--font-mono);letter-spacing:.1em}.profile-list strong{align-self:end;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}.profile-list em{color:#555d57;font:6px var(--font-mono);font-style:normal}.profile-list>button.selected small,.profile-list>button.selected em{color:#8c968e}.editor-shell{min-width:0}.rail-empty{display:grid;justify-items:center;padding:70px 20px;color:#606761;text-align:center}.rail-empty b{font:600 62px var(--font-display);color:#252a26}.rail-empty span{font-size:11px}.rail-empty small{margin-top:7px;font:7px var(--font-mono)}.model-workspace{position:relative;z-index:1;max-width:980px;margin:auto}.page-error{position:relative;z-index:2;max-width:1420px;margin:0 auto 12px;color:#ff8b78;font:8px var(--font-mono)}@media(max-width:900px){.topbar{grid-template-columns:1fr auto}.topbar nav{display:none}.hero{grid-template-columns:1fr}.hero p{max-width:480px}.workspace{grid-template-columns:1fr}.profile-rail{min-height:auto;border-right:0;border-bottom:1px solid var(--pg-line)}.profile-list{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.profiles-page{padding-inline:10px}.brand span,.back{font-size:0}.back:after{content:'↗';font-size:11px}.hero{margin-top:35px}.profile-list{grid-template-columns:1fr}.hero h1{font-size:44px}}
</style>
