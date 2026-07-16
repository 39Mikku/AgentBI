<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteAsset, listAssets } from '@/api/studio-assets'
import type { StudioAsset } from '@/api/chat-types'
import { useAuthStore } from '@/stores/auth'
import { assetContentUrl, formatAssetSize } from '@/utils/chat-attachments'

const router = useRouter()
const auth = useAuthStore()
const userId = computed(() => auth.email || 'local-user')
const assets = ref<StudioAsset[]>([])
const filter = ref<'all' | 'generated' | 'video' | 'uploaded' | 'docx'>('all')
const search = ref('')
const loading = ref(false)
const error = ref('')
const deleting = ref('')

const counts = computed(() => ({
  all: assets.value.length,
  generated: assets.value.filter((item) => item.source === 'generated' && item.kind === 'image').length,
  video: assets.value.filter((item) => item.kind === 'video').length,
  uploaded: assets.value.filter((item) => item.source === 'uploaded' && item.kind === 'image').length,
  docx: assets.value.filter((item) => item.kind === 'docx').length,
}))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const filters: { kind?: string; source?: string; search?: string } = {}
    if (filter.value === 'generated') { filters.source = 'generated'; filters.kind = 'image' }
    if (filter.value === 'video') filters.kind = 'video'
    if (filter.value === 'uploaded') { filters.source = 'uploaded'; filters.kind = 'image' }
    if (filter.value === 'docx') filters.kind = 'docx'
    if (search.value.trim()) filters.search = search.value.trim()
    assets.value = await listAssets(userId.value, filters)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '附件库加载失败'
  } finally {
    loading.value = false
  }
}

async function choose(value: typeof filter.value) {
  filter.value = value
  await load()
}

async function remove(asset: StudioAsset) {
  if (!window.confirm(`删除“${asset.filename}”？文件、识图转述和解析缓存都会被清除。`)) return
  deleting.value = asset.id
  try {
    await deleteAsset(userId.value, asset.id)
    assets.value = assets.value.filter((item) => item.id !== asset.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '删除失败'
  } finally {
    deleting.value = ''
  }
}

function openSource(asset: StudioAsset) {
  if (asset.source_conversation_id)
    void router.push({ path: '/chat', query: { conversation: asset.source_conversation_id } })
}

onMounted(load)
</script>

<template>
  <main class="asset-library">
    <header class="library-head">
      <button @click="router.push('/chat')">← 返回 Studio</button>
      <p>STUDIO ARCHIVE / ASSETS</p>
      <h1>附件，<em>归档成册。</em></h1>
      <span>对话生成图片、生成视频、上传图片与 DOCX 的统一索引。</span>
    </header>

    <section class="library-toolbar">
      <nav>
        <button :class="{ active: filter === 'all' }" @click="choose('all')">全部 <b>{{ counts.all }}</b></button>
        <button :class="{ active: filter === 'generated' }" @click="choose('generated')">生成图片 <b>{{ counts.generated }}</b></button>
        <button :class="{ active: filter === 'video' }" @click="choose('video')">生成视频 <b>{{ counts.video }}</b></button>
        <button :class="{ active: filter === 'uploaded' }" @click="choose('uploaded')">上传图片 <b>{{ counts.uploaded }}</b></button>
        <button :class="{ active: filter === 'docx' }" @click="choose('docx')">DOCX <b>{{ counts.docx }}</b></button>
      </nav>
      <form @submit.prevent="load"><input v-model="search" placeholder="搜索文件名、提示词或会话…" /><button>搜索</button></form>
    </section>

    <p v-if="error" class="library-error">{{ error }}</p>
    <div v-if="loading" class="library-loading"><i></i><span>正在整理资产索引</span></div>
    <section v-else-if="assets.length" class="asset-grid">
      <article v-for="(asset, index) in assets" :key="asset.id" :class="['asset-card', asset.kind]">
        <a v-if="asset.kind === 'image'" :href="assetContentUrl(asset.id, userId)" target="_blank" rel="noreferrer">
          <img :src="assetContentUrl(asset.id, userId)" :alt="asset.filename" />
        </a>
        <a v-else-if="asset.kind === 'video'" class="video-preview" :href="assetContentUrl(asset.id, userId)" target="_blank" rel="noreferrer">
          <video :src="assetContentUrl(asset.id, userId)" muted preload="metadata"></video><span>▶</span>
        </a>
        <a v-else class="doc-preview" :href="assetContentUrl(asset.id, userId)" download><b>DOCX</b><span>↓</span></a>
        <div class="asset-index">{{ String(index + 1).padStart(2, '0') }}</div>
        <div class="asset-copy">
          <small>{{ asset.source === 'generated' ? 'GENERATED' : 'UPLOADED' }} · {{ formatAssetSize(asset.size) }}</small>
          <strong>{{ asset.filename }}</strong>
          <p>{{ String(asset.metadata?.prompt || asset.source_conversation_title || '未命名来源') }}</p>
        </div>
        <div class="asset-actions">
          <button :disabled="!asset.source_conversation_id" @click="openSource(asset)">来源会话</button>
          <button class="danger" :disabled="deleting === asset.id" @click="remove(asset)">{{ deleting === asset.id ? '删除中' : '删除' }}</button>
        </div>
      </article>
    </section>
    <section v-else class="library-empty"><b>00</b><h2>这里还没有附件</h2><p>在 Studio 上传文件、生成图片或视频后，它们会汇总到这里。</p></section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
.asset-library{--acid:#d9ff36;min-height:100vh;padding:42px clamp(20px,6vw,92px) 80px;background:#151515;color:#efede7;font-family:Manrope,sans-serif}.library-head{max-width:1200px;margin:auto}.library-head>button{border:0;background:transparent;color:#96928a;padding:0;font:9px 'DM Mono';cursor:pointer}.library-head>p{margin:50px 0 11px;color:var(--acid);font:8px 'DM Mono';letter-spacing:.16em}.library-head h1{margin:0;font:600 clamp(48px,7vw,86px)/.94 'Playfair Display';letter-spacing:-.06em}.library-head h1 em{color:#77736d}.library-head>span{display:block;margin-top:18px;color:#8d8981;font-size:11px}.library-toolbar{max-width:1200px;margin:45px auto 25px;display:flex;justify-content:space-between;gap:25px;border-bottom:1px solid #3a3936}.library-toolbar nav{display:flex;gap:2px}.library-toolbar nav button{border:0;border-bottom:2px solid transparent;background:transparent;color:#77736c;padding:12px 15px;font:8px 'DM Mono';cursor:pointer}.library-toolbar nav button.active{border-bottom-color:var(--acid);color:#efede7}.library-toolbar nav b{margin-left:5px;color:#55524d}.library-toolbar form{display:flex;align-self:center;border-bottom:1px solid #58554f}.library-toolbar input{width:min(300px,32vw);border:0;outline:0;background:transparent;color:#eee;padding:9px;font:10px Manrope}.library-toolbar form button{border:0;background:transparent;color:var(--acid);font:8px 'DM Mono'}.asset-grid{max-width:1200px;margin:auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:#3c3b37;border:1px solid #3c3b37}.asset-card{position:relative;min-width:0;background:#1b1b1a}.asset-card>a:first-child{display:block;height:260px;overflow:hidden;background:#0d0d0c}.asset-card img{width:100%;height:100%;object-fit:cover;transition:transform .35s}.asset-card:hover img{transform:scale(1.025)}.doc-preview{display:flex!important;height:260px!important;align-items:center;justify-content:center;gap:16px;color:var(--acid);text-decoration:none;font:700 27px 'DM Mono';background:repeating-linear-gradient(135deg,#181817,#181817 12px,#1d1d1b 12px,#1d1d1b 24px)!important}.doc-preview span{font-size:18px}.asset-index{position:absolute;right:10px;top:10px;padding:5px;background:#111;color:var(--acid);font:7px 'DM Mono'}.asset-copy{padding:17px 17px 11px}.asset-copy small{color:var(--acid);font:7px 'DM Mono';letter-spacing:.11em}.asset-copy strong,.asset-copy p{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.asset-copy strong{margin-top:8px;font-size:11px}.asset-copy p{margin:6px 0 0;color:#77746e;font-size:8px}.asset-actions{display:flex;padding:0 17px 17px;gap:7px}.asset-actions button{border:1px solid #44413d;background:transparent;color:#aaa69e;padding:7px 9px;font:7px 'DM Mono';cursor:pointer}.asset-actions button:hover{border-color:var(--acid);color:var(--acid)}.asset-actions .danger{margin-left:auto;color:#d17466}.asset-actions button:disabled{opacity:.3}.library-loading,.library-empty{max-width:1200px;min-height:350px;margin:auto;display:grid;place-content:center;justify-items:center;color:#65615b}.library-loading i{width:30px;height:30px;border:2px solid #333;border-right-color:var(--acid);border-radius:50%;animation:spin .8s linear infinite}.library-loading span{margin-top:14px;font:8px 'DM Mono';letter-spacing:.12em}.library-empty b{font:700 70px Manrope;color:#282825}.library-empty h2{margin:5px;font:600 25px 'Playfair Display'}.library-empty p{font-size:9px}.library-error{max-width:1200px;margin:0 auto 16px;color:#ff7868;font:9px 'DM Mono'}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:900px){.asset-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){.library-toolbar{align-items:stretch;flex-direction:column}.library-toolbar nav{overflow-x:auto}.library-toolbar input{width:100%}.asset-grid{grid-template-columns:1fr}.asset-card>a:first-child,.doc-preview{height:230px!important}}
</style>
<style scoped>
.asset-card video{width:100%;height:100%;object-fit:cover;transition:transform .35s}.asset-card:hover video{transform:scale(1.025)}.video-preview{position:relative}.video-preview>span{position:absolute;left:50%;top:50%;display:grid;width:46px;height:46px;place-items:center;transform:translate(-50%,-50%);border:1px solid rgba(217,255,54,.65);border-radius:50%;background:rgba(10,10,10,.72);color:var(--acid);font-size:15px}
</style>
