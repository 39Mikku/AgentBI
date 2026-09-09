<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { generateImage } from '@/api/image-generation'
import type { GeneratedImage } from '@/api/image-generation-types'
import { uploadAsset } from '@/api/studio-assets'
import { nameStickers } from '@/api/toolbox-emoji'
import { useWorkspaceStore } from '@/stores/workspace'
import { useChatStore } from '@/stores/chat'
import {
  buildStickerPrompt,
  cutStickerSheet,
  DEFAULT_CUT_OPTIONS,
  downloadStickerZip,
  safeStickerFilename,
  type CutSticker,
  type StickerCutOptions,
} from '@/toolbox/emoji-sticker'
import { assetContentUrl } from '@/utils/chat-attachments'
import { fileToDataUrl, formatBytes, prepareImageFile } from '@/utils/image-source'

const router = useRouter()
const workspace = useWorkspaceStore()
const chat = useChatStore()
const userId = computed(() => workspace.userId)

const styles = [
  { id: 'kawaii', mark: 'KA', name: '软萌漫画', note: 'ROUND / POP', prompt: '软萌日系漫画贴纸，圆润线条，高饱和配色，夸张可爱的表情' },
  { id: 'pixel', mark: 'PX', name: '像素游戏', note: '16-BIT / RETRO', prompt: '精致 16-bit 像素游戏美术，清晰像素边缘，复古掌机配色' },
  { id: 'print', mark: 'PR', name: '复古印刷', note: 'RISOGRAPH / GRAIN', prompt: '复古丝网印刷与 risograph 颗粒质感，有限色板，粗线条' },
  { id: 'clay', mark: 'CL', name: '黏土玩偶', note: 'SOFT 3D / MINI', prompt: '精致软陶黏土玩偶，微缩摄影质感，柔和棚拍光线' },
  { id: 'water', mark: 'WC', name: '透明水彩', note: 'WASH / PAPER', prompt: '轻盈透明水彩插画，柔软晕染，细腻纸张纹理' },
  { id: 'ink', mark: 'IN', name: '极简墨线', note: 'MONO / GESTURE', prompt: '极简黑白墨线速写，动作感强，少量点睛色' },
]

const subject = ref('')
const selectedStyle = ref(styles[0]!.id)
const customStyle = ref('')
const includeText = ref(true)
const aiNaming = ref(true)
const referenceImage = ref<string | null>(null)
const referenceName = ref('')
const sheet = ref<GeneratedImage | null>(null)
const sheetSourceUrl = ref('')
const sheetOrigin = ref<'generated' | 'uploaded' | ''>('')
const stickers = ref<CutSticker[]>([])
const busy = ref<'preparing' | 'generating' | 'cutting' | 'naming' | ''>('')
const error = ref('')
const notice = ref('')
const namingModel = ref('')
const advancedOpen = ref(false)
const cutOptions = ref<StickerCutOptions>({ ...DEFAULT_CUT_OPTIONS })

const activeStyle = computed(() => styles.find((item) => item.id === selectedStyle.value) ?? styles[0]!)
const effectiveStyle = computed(() => customStyle.value.trim() || activeStyle.value.prompt)
const canGenerate = computed(() => !busy.value)
const statusLabel = computed(() => {
  if (busy.value === 'preparing') return '正在压缩并上传贴纸表'
  if (busy.value === 'generating') return '正在交付给生图服务'
  if (busy.value === 'cutting') return '正在扫描贴纸边界'
  if (busy.value === 'naming') return '识图模型正在命名'
  return ''
})

async function selectReference(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = ''
  try {
    referenceImage.value = await fileToDataUrl(file, 10 * 1024 * 1024)
    referenceName.value = file.name
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '参考图读取失败'
  }
}

function clearReference() {
  referenceImage.value = null
  referenceName.value = ''
}

async function generate() {
  if (!canGenerate.value) return
  error.value = ''
  notice.value = ''
  namingModel.value = ''
  stickers.value = []
  busy.value = 'generating'
  try {
    sheet.value = await generateImage({
      user_id: userId.value,
      prompt: buildStickerPrompt({
        subject: subject.value,
        style: effectiveStyle.value,
        includeText: includeText.value,
        hasReference: Boolean(referenceImage.value),
      }),
      aspect_ratio: 'square',
      provider_id: chat.preferences.providerId,
      scope_id: 'toolbox-emoji',
      reference_image_data_url: referenceImage.value || undefined,
    })
    sheetSourceUrl.value = sheet.value.url
    sheetOrigin.value = 'generated'
    notice.value = '整张贴纸表已进入附件库'
    await recut()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '贴纸生成失败'
  } finally {
    busy.value = ''
  }
}

async function selectStickerSheet(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || busy.value) return
  error.value = ''
  notice.value = ''
  namingModel.value = ''
  stickers.value = []
  busy.value = 'preparing'
  try {
    const prepared = await prepareImageFile(file)
    const asset = await uploadAsset(userId.value, prepared)
    sheet.value = null
    sheetSourceUrl.value = assetContentUrl(asset.id, userId.value)
    sheetOrigin.value = 'uploaded'
    notice.value =
      prepared.size < file.size
        ? `现成贴纸表已压缩至 ${formatBytes(prepared.size)} 并进入附件库`
        : '现成贴纸表已进入附件库'
    busy.value = ''
    await recut()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '贴纸表上传失败'
  } finally {
    if (busy.value === 'preparing') busy.value = ''
  }
}

async function recut() {
  if (!sheetSourceUrl.value || busy.value === 'cutting') return
  error.value = ''
  busy.value = 'cutting'
  try {
    stickers.value = await cutStickerSheet(sheetSourceUrl.value, cutOptions.value)
    if (!stickers.value.length) throw new Error('没有识别到独立贴纸，请提高背景容差或降低最小区域')
    if (aiNaming.value) await applyAiNames('batch')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '贴纸切割失败'
  } finally {
    if (busy.value === 'cutting') busy.value = ''
  }
}

async function applyAiNames(strategy: 'batch' | 'individual' = 'batch') {
  if (!stickers.value.length) return
  busy.value = 'naming'
  try {
    const result = await nameStickers({
      user_id: userId.value,
      strategy,
      images: stickers.value.slice(0, 16).map((item) => ({ id: item.id, data_url: item.dataUrl })),
    })
    const names = new Map(result.names.map((item) => [item.id, item.name]))
    stickers.value = stickers.value.map((item) => ({ ...item, name: names.get(item.id) || item.name }))
    namingModel.value = result.model
  } catch (reason) {
    notice.value = `贴纸已经切好，但 AI 命名未完成：${reason instanceof Error ? reason.message : '请求失败'}`
  } finally {
    busy.value = ''
  }
}

function removeSticker(id: string) {
  stickers.value = stickers.value.filter((item) => item.id !== id)
}

function downloadOne(sticker: CutSticker, index: number) {
  const url = URL.createObjectURL(sticker.blob)
  const link = document.createElement('a')
  link.href = url
  link.download = safeStickerFilename(sticker.name, index)
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function downloadAll() {
  if (stickers.value.length) await downloadStickerZip(stickers.value, 'AgentBI-中文表情包.zip')
}

onMounted(async () => {
  if (!chat.preferences.providerId) {
    try {
      await chat.restorePreferences(userId.value)
    } catch {
      notice.value = '尚未读取 Studio 模型配置；Lite 模式生成前请先配置提供商。'
    }
  }
})
</script>

<template>
  <main class="emoji-workbench">
    <div class="paper-noise" aria-hidden="true"></div>
    <header class="workbench-nav">
      <button class="brand" @click="router.push('/toolbox')"><i></i>AGENTBI <span>/ EMOJI PRESS</span></button>
      <nav><button @click="router.push('/attachments')">附件库</button><button @click="router.push('/toolbox')">返回工具箱 ↗</button></nav>
    </header>

    <section class="workbench-title">
      <div><p>TOOLBOX 005 / STICKER PRODUCTION</p><h1>把一个角色，<em>印成十六种反应。</em></h1></div>
      <aside><b>01</b> GENERATE <i></i><b>02</b> CUT <i></i><b>03</b> NAME <i></i><b>04</b> PACK</aside>
    </section>

    <section class="press-grid">
      <aside class="control-rail">
        <div class="section-label"><span>01</span><b>创作规格</b><small>CREATIVE BRIEF</small></div>
        <label class="subject-field"><span>角色与表情主题 · 可留空</span><textarea v-model="subject" maxlength="2000" rows="4" placeholder="留空则根据参考图创作；没有参考图时自由设计原创角色"></textarea><small>{{ subject.length }} / 2000</small></label>

        <div class="style-head"><span>视觉风格</span><small>{{ activeStyle.note }}</small></div>
        <div class="style-grid">
          <button v-for="style in styles" :key="style.id" :class="{ active: selectedStyle === style.id }" @click="selectedStyle = style.id"><b>{{ style.mark }}</b><span>{{ style.name }}</span></button>
        </div>
        <label class="custom-style"><span>自定义风格覆盖</span><input v-model="customStyle" maxlength="300" placeholder="留空则使用上方预设" /></label>

        <div class="switch-stack">
          <label><span><b>贴纸配文字</b><small>默认加入简短中文情绪文字</small></span><input v-model="includeText" type="checkbox" /><i></i></label>
          <label><span><b>AI 中文命名</b><small>生成后调用当前识图模型</small></span><input v-model="aiNaming" type="checkbox" /><i></i></label>
        </div>

        <div class="reference-block">
          <div><span>角色参考图</span><small>OPTIONAL / PNG JPG WEBP</small></div>
          <label v-if="!referenceImage" class="reference-drop"><input type="file" accept="image/png,image/jpeg,image/webp" @change="selectReference" /><b>＋</b><span>添加参考图</span></label>
          <div v-else class="reference-ready"><img :src="referenceImage" alt="角色参考图" /><span><b>{{ referenceName }}</b><small>将随提示词一并发送</small></span><button @click="clearReference">移除</button></div>
        </div>

        <button class="advanced-toggle" @click="advancedOpen = !advancedOpen"><span>高级切图参数</span><b>{{ advancedOpen ? '−' : '+' }}</b></button>
        <div v-if="advancedOpen" class="advanced-panel">
          <label>背景容差 <b>{{ cutOptions.backgroundTolerance }}</b><input v-model.number="cutOptions.backgroundTolerance" type="range" min="8" max="80" /></label>
          <label>区域合并 <b>{{ cutOptions.mergeGap }}</b><input v-model.number="cutOptions.mergeGap" type="range" min="0" max="48" /></label>
          <label>最小区域 <b>{{ cutOptions.minArea }}</b><input v-model.number="cutOptions.minArea" type="range" min="20" max="600" step="10" /></label>
          <label>白色描边 <b>{{ cutOptions.strokeWidth }}</b><input v-model.number="cutOptions.strokeWidth" type="range" min="0" max="16" /></label>
        </div>

        <button class="generate-button" :disabled="!canGenerate" @click="generate"><span>{{ busy ? statusLabel : '开始印制贴纸表' }}</span><b>{{ busy ? '•••' : 'PRINT ↗' }}</b></button>
        <label class="sheet-upload-button" :class="{ disabled: Boolean(busy) }">
          <input type="file" accept="image/png,image/jpeg,image/webp" :disabled="Boolean(busy)" @change="selectStickerSheet" />
          <span>上传现成贴纸表</span><b>LOCAL ↗</b>
        </label>
        <p v-if="error" class="rail-error">{{ error }}</p><p v-if="notice" class="rail-notice">{{ notice }}</p>
      </aside>

      <section class="sheet-stage">
        <header><div><span>02</span><b>母版预览</b></div><small>{{ sheet ? `${sheet.model} / ${sheet.mode.toUpperCase()}` : sheetOrigin === 'uploaded' ? 'LOCAL UPLOAD / 1:1' : 'MASTER SHEET / 1:1' }}</small></header>
        <div class="sheet-frame" :class="{ empty: !sheetSourceUrl }">
          <template v-if="sheetSourceUrl"><img :src="sheetSourceUrl" alt="完整贴纸表" /><div class="crop-grid" aria-hidden="true"><i v-for="n in 16" :key="n"></i></div></template>
          <div v-else class="sheet-placeholder"><span>16</span><b>一张母版<br>十六个独立反应</b><small>AI 生成，或上传已有贴纸表</small></div>
          <div v-if="busy" class="stage-loader"><i></i><span>{{ statusLabel }}</span></div>
        </div>
        <footer><span>{{ sheetOrigin ? (sheetOrigin === 'generated' ? '生成母版已自动归入附件库' : '上传母版已归入附件库') : 'PURE BACKGROUND / WIDE GUTTERS / AUTO CUT' }}</span><button :disabled="!sheetSourceUrl || Boolean(busy)" @click="recut">重新切割</button></footer>
      </section>

      <section class="sticker-tray">
        <header><div><span>03</span><b>成品托盘</b></div><small>{{ String(stickers.length).padStart(2, '0') }} PIECES</small></header>
        <div v-if="stickers.length" class="tray-grid">
          <article v-for="(sticker, index) in stickers" :key="sticker.id">
            <div class="sticker-preview"><img :src="sticker.dataUrl" :alt="sticker.name" /><span>{{ String(index + 1).padStart(2, '0') }}</span></div>
            <input v-model="sticker.name" maxlength="32" aria-label="贴纸名称" />
            <div><button @click="downloadOne(sticker, index)">PNG ↓</button><button @click="removeSticker(sticker.id)">移除</button></div>
          </article>
        </div>
        <div v-else class="tray-empty"><i></i><i></i><i></i><i></i><p>切割完成后，透明贴纸会在这里逐张装盘。</p></div>
        <footer><span v-if="namingModel">命名模型 · {{ namingModel }}</span><span v-else>中文命名可随时手动修改</span><button v-if="stickers.length && aiNaming" :disabled="Boolean(busy)" @click="applyAiNames('individual')">逐张重新命名</button><button class="zip" :disabled="!stickers.length" @click="downloadAll">下载 ZIP · {{ stickers.length }}</button></footer>
      </section>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700;800&family=Noto+Serif+SC:wght@600;700&display=swap');
*{box-sizing:border-box}.emoji-workbench{--ink:#161613;--paper:#edeae1;--acid:#d9ff36;--red:#ff5b45;--blue:#3c65ff;position:relative;min-height:100vh;overflow:hidden;background:var(--paper);color:var(--ink);padding:0 clamp(18px,3.6vw,58px) 54px;font-family:Manrope,'Microsoft YaHei',sans-serif}.paper-noise{position:fixed;inset:0;pointer-events:none;opacity:.08;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.3'/%3E%3C/svg%3E")}.workbench-nav{position:relative;z-index:2;height:72px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #b9b5aa}.workbench-nav button{border:0;background:transparent;color:inherit;cursor:pointer}.brand{display:flex;align-items:center;gap:9px;font:700 var(--control-font-size) 'DM Mono';letter-spacing:.13em}.brand i{width:17px;height:17px;border:1px solid var(--ink);box-shadow:4px 4px 0 var(--acid)}.brand span{color:#77736b;font-weight:400}.workbench-nav nav{display:flex;gap:2px}.workbench-nav nav button{padding:9px 12px;font:var(--control-font-size) 'DM Mono';color:#6d6961}.workbench-nav nav button:hover{background:var(--ink);color:var(--acid)}.workbench-title{position:relative;z-index:1;display:flex;align-items:end;justify-content:space-between;gap:40px;padding:43px 0 38px}.workbench-title p{margin:0 0 10px;color:#77736b;font:8px 'DM Mono';letter-spacing:.16em}.workbench-title h1{margin:0;font:700 clamp(38px,5.4vw,74px)/.98 'Noto Serif SC',serif;letter-spacing:-.075em}.workbench-title h1 em{font-style:normal;color:#969188}.workbench-title aside{display:flex;align-items:center;padding-bottom:7px;color:#817d74;font:7px 'DM Mono';letter-spacing:.08em}.workbench-title aside b{color:var(--ink)}.workbench-title aside i{width:30px;height:1px;margin:0 8px;background:#aaa69c}.press-grid{position:relative;z-index:1;display:grid;grid-template-columns:minmax(250px,310px) minmax(390px,1fr) minmax(330px,.9fr);max-width:1660px;margin:auto;border:1px solid var(--ink);background:var(--ink);gap:1px}.control-rail,.sheet-stage,.sticker-tray{min-width:0;background:var(--paper)}.control-rail{padding:20px}.section-label,.sheet-stage>header,.sticker-tray>header{display:flex;align-items:center;gap:10px}.section-label>span,.sheet-stage>header span,.sticker-tray>header span{display:grid;width:25px;height:25px;place-items:center;background:var(--ink);color:var(--acid);font:7px 'DM Mono'}.section-label b,.sheet-stage>header b,.sticker-tray>header b{font-size:10px}.section-label small{margin-left:auto;color:#8a867e;font:7px 'DM Mono'}.subject-field,.custom-style{position:relative;display:grid;gap:7px;margin-top:22px}.subject-field>span,.custom-style>span,.style-head>span,.reference-block>div:first-child span{font:700 8px 'DM Mono';letter-spacing:.06em}.subject-field textarea,.custom-style input{width:100%;border:1px solid #a9a59b;outline:0;background:#f5f2ea;color:var(--ink);padding:10px;resize:vertical;font:10px/1.55 Manrope}.subject-field textarea:focus,.custom-style input:focus{border-color:var(--blue);box-shadow:3px 3px 0 rgba(60,101,255,.18)}.subject-field>small{position:absolute;right:8px;bottom:7px;color:#aaa59b;font:6px 'DM Mono'}.style-head{display:flex;justify-content:space-between;margin-top:20px}.style-head small{color:#8a867e;font:6px 'DM Mono'}.style-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:8px;background:#aaa59b;border:1px solid #aaa59b}.style-grid button{min-height:59px;border:0;background:#e7e3d9;color:#55514b;padding:8px;text-align:left;cursor:pointer}.style-grid button b{display:block;font:700 var(--control-font-size) 'DM Mono'}.style-grid button span{display:block;margin-top:7px;font-size:var(--control-font-size)}.style-grid button.active{background:var(--acid);color:#111}.custom-style{margin-top:10px}.custom-style input{height:36px}.switch-stack{margin-top:17px;border-top:1px solid #aaa59b}.switch-stack label{position:relative;display:flex;align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid #c7c2b8;cursor:pointer}.switch-stack label>span{display:grid;gap:3px}.switch-stack label b{font-size:var(--control-font-size)}.switch-stack label small{color:#89857c;font:var(--control-font-size) 'DM Mono'}.switch-stack input{position:absolute;opacity:0}.switch-stack i{position:relative;width:31px;height:16px;border:1px solid #8c887f;background:#d8d4ca}.switch-stack i:after{content:'';position:absolute;left:2px;top:2px;width:10px;height:10px;background:#7f7b73;transition:.2s}.switch-stack input:checked+i{background:var(--ink);border-color:var(--ink)}.switch-stack input:checked+i:after{left:16px;background:var(--acid)}.reference-block{margin-top:17px}.reference-block>div:first-child{display:flex;justify-content:space-between}.reference-block small{color:#8a867e;font:6px 'DM Mono'}.reference-drop{position:relative;display:flex;align-items:center;gap:9px;height:47px;margin-top:8px;border:1px dashed #99958c;cursor:pointer}.reference-drop input{position:absolute;inset:0;opacity:0}.reference-drop b{display:grid;width:45px;height:100%;place-items:center;border-right:1px dashed #99958c;font:300 21px 'DM Mono'}.reference-drop span{font-size:var(--control-font-size)}.reference-ready{display:grid!important;grid-template-columns:44px minmax(0,1fr) auto;align-items:center;gap:9px;margin-top:8px;border:1px solid #99958c;padding:5px}.reference-ready img{width:44px;height:44px;object-fit:cover}.reference-ready>span{display:grid;min-width:0}.reference-ready b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:8px}.reference-ready button{border:0;background:transparent;color:var(--red);font:var(--control-font-size) 'DM Mono';cursor:pointer}.advanced-toggle{display:flex;width:100%;justify-content:space-between;margin-top:17px;padding:9px 0;border:0;border-top:1px solid #aaa59b;border-bottom:1px solid #aaa59b;background:transparent;color:inherit;font:var(--control-font-size) 'DM Mono';cursor:pointer}.advanced-panel{display:grid;gap:10px;padding:12px 0}.advanced-panel label{display:grid;grid-template-columns:1fr auto;gap:5px;color:#77736b;font:7px 'DM Mono'}.advanced-panel input{grid-column:1/-1;width:100%;accent-color:var(--ink)}.generate-button,.sheet-upload-button{display:flex;width:100%;height:48px;align-items:center;justify-content:space-between;padding:0 14px;font:700 var(--control-font-size) Manrope;cursor:pointer}.generate-button{margin-top:17px;border:0;background:var(--ink);color:#f4f1e9}.generate-button b{color:var(--acid);font:var(--control-font-size) 'DM Mono'}.generate-button:disabled{opacity:.42;cursor:not-allowed}.sheet-upload-button{position:relative;height:38px;margin-top:6px;border:1px solid #858078;background:transparent;color:var(--ink)}.sheet-upload-button input{position:absolute;inset:0;opacity:0;cursor:pointer}.sheet-upload-button b{font:var(--control-font-size) 'DM Mono';color:#716d65}.sheet-upload-button:hover{background:#dfdbd1}.sheet-upload-button.disabled{opacity:.42;cursor:not-allowed}.sheet-upload-button.disabled input{cursor:not-allowed}.rail-error,.rail-notice{margin:10px 0 0;font:7px/1.5 'DM Mono'}.rail-error{color:#d63f31}.rail-notice{color:#687c1d}.sheet-stage,.sticker-tray{display:flex;min-height:690px;flex-direction:column;padding:20px}.sheet-stage>header,.sticker-tray>header{justify-content:space-between}.sheet-stage>header>div,.sticker-tray>header>div{display:flex;align-items:center;gap:9px}.sheet-stage>header small,.sticker-tray>header small{color:#77736b;font:7px 'DM Mono'}.sheet-frame{position:relative;display:grid;flex:1;place-items:center;margin-top:18px;overflow:hidden;border:1px solid #a6a198;background:#d8d4ca}.sheet-frame:before{content:'';position:absolute;inset:0;background-image:linear-gradient(45deg,#cbc7bc 25%,transparent 25%),linear-gradient(-45deg,#cbc7bc 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#cbc7bc 75%),linear-gradient(-45deg,transparent 75%,#cbc7bc 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}.sheet-frame>img{position:relative;z-index:1;width:100%;height:100%;object-fit:contain;background:#fff}.crop-grid{position:absolute;z-index:2;inset:0;display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,1fr);pointer-events:none;opacity:.22}.crop-grid i{border-right:1px dashed #222;border-bottom:1px dashed #222}.sheet-placeholder{position:relative;z-index:1;text-align:center}.sheet-placeholder>span{display:block;font:800 clamp(70px,9vw,150px)/.8 Manrope;letter-spacing:-.1em;color:#bbb6aa}.sheet-placeholder b{display:block;margin-top:26px;font:700 clamp(18px,2vw,28px)/1.1 'Noto Serif SC'}.sheet-placeholder small{display:block;margin-top:12px;color:#77736b;font:7px 'DM Mono'}.stage-loader{position:absolute;z-index:4;inset:0;display:grid;place-content:center;justify-items:center;background:rgba(237,234,225,.9);backdrop-filter:blur(5px)}.stage-loader i{width:42px;height:42px;border:2px solid #aaa59a;border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite}.stage-loader span{margin-top:13px;font:8px 'DM Mono'}.sheet-stage>footer,.sticker-tray>footer{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-top:14px}.sheet-stage>footer span,.sticker-tray>footer span{color:#77736b;font:6px 'DM Mono'}.sheet-stage>footer button,.sticker-tray>footer button{border:1px solid #858078;background:transparent;color:inherit;padding:7px 9px;font:var(--control-font-size) 'DM Mono';cursor:pointer}.sheet-stage>footer button:disabled,.sticker-tray>footer button:disabled{opacity:.3}.tray-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:18px;background:#aaa59b;border:1px solid #aaa59b;max-height:590px;overflow:auto}.tray-grid article{min-width:0;background:#e5e1d7;padding:7px}.sticker-preview{position:relative;aspect-ratio:1;display:grid;place-items:center;overflow:hidden;background:repeating-conic-gradient(#d2cec4 0 25%,#ddd9cf 0 50%) 50%/14px 14px}.sticker-preview img{width:100%;height:100%;object-fit:contain}.sticker-preview span{position:absolute;right:3px;top:3px;background:var(--ink);color:var(--acid);padding:3px;font:6px 'DM Mono'}.tray-grid input{width:100%;height:26px;border:0;border-bottom:1px solid #aaa59b;outline:0;background:transparent;text-align:center;font:8px Manrope}.tray-grid article>div:last-child{display:flex;justify-content:space-between;margin-top:5px}.tray-grid button{border:0;background:transparent;color:#77736b;padding:2px;font:var(--control-font-size) 'DM Mono';cursor:pointer}.tray-grid button:hover{color:var(--blue)}.tray-empty{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-content:center;flex:1;padding:35px}.tray-empty i{aspect-ratio:1;border:1px dashed #b1aca1;background:linear-gradient(135deg,transparent 48%,#d6d2c8 49% 51%,transparent 52%)}.tray-empty p{grid-column:1/-1;margin:12px 0 0;text-align:center;color:#8a867d;font:7px/1.6 'DM Mono'}.sticker-tray>footer{margin-top:auto;flex-wrap:wrap}.sticker-tray>footer .zip{margin-left:auto;border-color:var(--ink);background:var(--ink);color:var(--acid)}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:1250px){.press-grid{grid-template-columns:290px 1fr}.sticker-tray{grid-column:1/-1;min-height:520px}.tray-grid{grid-template-columns:repeat(6,1fr)}}@media(max-width:820px){.emoji-workbench{padding-inline:14px}.workbench-title{align-items:start;flex-direction:column}.workbench-title aside{display:none}.press-grid{grid-template-columns:1fr}.sheet-stage,.sticker-tray{min-height:580px}.tray-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:480px){.workbench-nav nav button:first-child{display:none}.workbench-title h1{font-size:40px}.style-grid{grid-template-columns:1fr 1fr}.tray-grid{grid-template-columns:1fr 1fr}.sheet-stage,.sticker-tray{padding:13px}}
</style>
