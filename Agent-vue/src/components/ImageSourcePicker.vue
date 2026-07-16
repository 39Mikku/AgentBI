<script setup lang="ts">
import { computed, ref } from 'vue'

import { generateImage } from '@/api/image-generation'
import type { ImageAspectRatio } from '@/api/image-generation-types'
import { fileToDataUrl, formatBytes, generatedImageToDataUrl } from '@/utils/image-source'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    userId: string
    providerId?: string
    scopeId?: string
    maxBytes?: number
    theme?: 'light' | 'dark'
    shape?: 'rounded' | 'circle'
    disabled?: boolean
    allowRemove?: boolean
  }>(),
  {
    modelValue: null,
    providerId: undefined,
    scopeId: 'direct-image',
    maxBytes: 1_400_000,
    theme: 'light',
    shape: 'rounded',
    disabled: false,
    allowRemove: true,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
  error: [message: string]
}>()

const mode = ref<'upload' | 'generate'>('upload')
const prompt = ref('')
const aspectRatio = ref<ImageAspectRatio>('square')
const busy = ref(false)
const error = ref('')
const initials = computed(() => (props.scopeId || 'AI').slice(0, 2).toUpperCase())

function report(reason: unknown) {
  error.value = reason instanceof Error ? reason.message : '图片处理失败'
  emit('error', error.value)
}

async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  busy.value = true
  error.value = ''
  try {
    emit('update:modelValue', await fileToDataUrl(file, props.maxBytes))
  } catch (reason) {
    report(reason)
  } finally {
    busy.value = false
  }
}

async function generate() {
  const description = prompt.value.trim()
  if (!description || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const image = await generateImage({
      user_id: props.userId,
      prompt: description,
      aspect_ratio: aspectRatio.value,
      provider_id: props.providerId || undefined,
      scope_id: props.scopeId,
    })
    emit('update:modelValue', await generatedImageToDataUrl(image.url))
  } catch (reason) {
    report(reason)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="image-source" :data-theme="theme" :data-shape="shape">
    <header>
      <div class="source-preview">
        <img v-if="modelValue" :src="modelValue" alt="当前图片预览" />
        <span v-else>{{ initials }}</span>
        <i v-if="busy"></i>
      </div>
      <div class="source-heading">
        <strong>图片来源</strong>
        <small>{{ modelValue ? '当前图片已就绪，可继续替换' : '上传现有图片，或用一句描述生成' }}</small>
      </div>
      <button v-if="modelValue && allowRemove" type="button" class="remove" :disabled="disabled || busy" @click="emit('update:modelValue', null)">移除</button>
    </header>

    <nav aria-label="图片来源">
      <button type="button" :class="{ active: mode === 'upload' }" @click="mode = 'upload'">上传图片</button>
      <button type="button" :class="{ active: mode === 'generate' }" @click="mode = 'generate'">描述生图</button>
    </nav>

    <label v-if="mode === 'upload'" class="drop-zone">
      <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" :disabled="disabled || busy" @change="upload" />
      <span><b>{{ busy ? '正在读取…' : '选择本地图片' }}</b><small>PNG / JPG / WebP / GIF · {{ formatBytes(maxBytes) }}</small></span>
      <i>↗</i>
    </label>
    <form v-else class="prompt-zone" @submit.prevent="generate">
      <textarea v-model="prompt" rows="3" maxlength="20000" :disabled="disabled || busy" placeholder="直接写图片描述；这里不会调用聊天模型改写。"></textarea>
      <div>
        <label>画幅
          <select v-model="aspectRatio" :disabled="disabled || busy">
            <option value="square">方形 1:1</option>
            <option value="landscape">横向 3:2</option>
            <option value="portrait">竖向 2:3</option>
          </select>
        </label>
        <button :disabled="disabled || busy || !prompt.trim()">{{ busy ? '生成中…' : '生成并应用 ↗' }}</button>
      </div>
    </form>
    <p v-if="error" class="source-error">{{ error }}</p>
  </section>
</template>

<style scoped>
.image-source{--bg:#f6f4ee;--panel:#ebe8df;--ink:#171717;--muted:#77736a;--line:#aaa59b;--accent:#171717;--accent-ink:#d9ff36;display:grid;gap:10px;color:var(--ink);font-family:Manrope,sans-serif}.image-source[data-theme=dark]{--bg:#0a0f0d;--panel:#101614;--ink:#c7d2cc;--muted:#5f6d66;--line:rgba(255,255,255,.12);--accent:#9fffd8;--accent-ink:#07110e}.image-source>header{display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center}.source-preview{position:relative;width:50px;height:50px;overflow:hidden;border:1px solid var(--line);border-radius:10px;background:var(--panel)}[data-shape=circle] .source-preview{border-radius:50%}.source-preview img{width:100%;height:100%;object-fit:cover}.source-preview span{display:grid;place-items:center;width:100%;height:100%;color:var(--muted);font:700 10px 'DM Mono'}.source-preview i{position:absolute;inset:0;border:2px solid transparent;border-top-color:var(--accent);border-radius:inherit;animation:sourceSpin .8s linear infinite}.source-heading{display:grid;gap:4px}.source-heading strong{font-size:11px}.source-heading small{color:var(--muted);font:8px/1.45 'DM Mono'}.remove{border:0;background:transparent;color:var(--muted);font:8px 'DM Mono';cursor:pointer}.image-source nav{display:grid;grid-template-columns:1fr 1fr;padding:3px;border:1px solid var(--line);background:var(--panel)}.image-source nav button{height:31px;border:0;background:transparent;color:var(--muted);font:8px 'DM Mono';cursor:pointer}.image-source nav button.active{background:var(--accent);color:var(--accent-ink)}.drop-zone{position:relative;display:flex;align-items:center;justify-content:space-between;min-height:58px;padding:0 13px;border:1px dashed var(--line);background:var(--bg);cursor:pointer}.drop-zone input{position:absolute;inset:0;opacity:0;cursor:pointer}.drop-zone span{display:grid;gap:4px}.drop-zone b{font-size:10px}.drop-zone small{color:var(--muted);font:7px 'DM Mono'}.drop-zone>i{font-style:normal}.prompt-zone{display:grid;gap:8px}.prompt-zone textarea{width:100%;box-sizing:border-box;resize:vertical;border:1px solid var(--line);outline:0;background:var(--bg);color:var(--ink);padding:10px;font:10px/1.55 Manrope}.prompt-zone>div{display:flex;align-items:end;justify-content:space-between;gap:10px}.prompt-zone label{display:grid;gap:4px;color:var(--muted);font:7px 'DM Mono'}.prompt-zone select{height:31px;border:1px solid var(--line);background:var(--bg);color:var(--ink);padding:0 8px}.prompt-zone button{height:34px;border:0;background:var(--accent);color:var(--accent-ink);padding:0 13px;font:700 8px Manrope;cursor:pointer}.prompt-zone button:disabled{opacity:.4;cursor:wait}.source-error{margin:0;color:#e36b5d;font:8px/1.5 'DM Mono'}@keyframes sourceSpin{to{transform:rotate(360deg)}}
</style>
