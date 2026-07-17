<script setup lang="ts">
import { computed, ref } from 'vue'

import { generateImage } from '@/api/image-generation'
import { uploadAsset } from '@/api/studio-assets'
import { assetContentUrl } from '@/utils/chat-attachments'


const props = defineProps<{
  modelValue: string | null
  userId: string
  kind: 'avatar' | 'background'
  providerId?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [assetId: string | null] }>()

const mode = ref<'upload' | 'generate'>('upload')
const prompt = ref('')
const busy = ref(false)
const error = ref('')
const generatedPreview = ref('')
const preview = computed(() =>
  generatedPreview.value ||
  (props.modelValue ? assetContentUrl(props.modelValue, props.userId) : ''),
)

async function chooseFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  busy.value = true
  error.value = ''
  try {
    const asset = await uploadAsset(props.userId, file)
    generatedPreview.value = ''
    emit('update:modelValue', asset.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '图片上传失败'
  } finally {
    busy.value = false
    ;(event.target as HTMLInputElement).value = ''
  }
}

async function generate() {
  if (!prompt.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const image = await generateImage({
      user_id: props.userId,
      prompt: prompt.value.trim(),
      aspect_ratio: props.kind === 'avatar' ? 'square' : 'landscape',
      provider_id: props.providerId,
      scope_id: `playground-${props.kind}`,
    })
    generatedPreview.value = image.url
    emit('update:modelValue', image.id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '图片生成失败'
  } finally {
    busy.value = false
  }
}

function clear() {
  generatedPreview.value = ''
  emit('update:modelValue', null)
}
</script>

<template>
  <section class="asset-picker" :data-kind="kind">
    <div class="asset-preview" :class="{ empty: !preview }">
      <img v-if="preview" :src="preview" alt="" />
      <span v-else aria-hidden="true"><i></i><b></b></span>
      <em v-if="busy"></em>
    </div>
    <div class="asset-controls">
      <header>
        <div>
          <strong>{{ kind === 'avatar' ? '角色头像' : '场景背景' }}</strong>
          <small>{{ kind === 'avatar' ? '方形图像，叙事中的视觉锚点' : '横向图像，作为会话氛围底图' }}</small>
        </div>
        <button v-if="modelValue" type="button" @click="clear">移除</button>
      </header>
      <nav>
        <button type="button" :class="{ active: mode === 'upload' }" @click="mode = 'upload'">上传</button>
        <button type="button" :class="{ active: mode === 'generate' }" @click="mode = 'generate'">生成</button>
      </nav>
      <label v-if="mode === 'upload'" class="upload-zone">
        <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" :disabled="busy" @change="chooseFile" />
        <span>选择本地图片</span><b>↗</b>
      </label>
      <div v-else class="generate-zone">
        <textarea v-model="prompt" rows="2" :placeholder="kind === 'avatar' ? '描述角色外观与画面风格…' : '描述故事发生的场景与光线…'"></textarea>
        <button type="button" :disabled="busy || !prompt.trim()" @click="generate">{{ busy ? '生成中' : '生成并应用' }}</button>
      </div>
      <p v-if="error">{{ error }}</p>
    </div>
  </section>
</template>

<style scoped>
.asset-picker{display:grid;grid-template-columns:86px minmax(0,1fr);gap:16px;align-items:start}.asset-picker[data-kind=background]{grid-template-columns:160px minmax(0,1fr)}.asset-preview{position:relative;aspect-ratio:1;overflow:hidden;border:1px solid var(--pg-line);background:#121514}.asset-picker[data-kind=background] .asset-preview{aspect-ratio:16/9}.asset-preview img{width:100%;height:100%;object-fit:cover}.asset-preview.empty span{position:absolute;inset:0}.asset-preview.empty i,.asset-preview.empty b{position:absolute;display:block}.asset-preview.empty i{width:32%;height:32%;left:34%;top:34%;border:1px solid #4e5651;border-radius:50%}.asset-preview.empty b{width:54%;height:1px;left:23%;top:50%;background:#3d4540;transform:rotate(-35deg)}.asset-preview em{position:absolute;inset:8px;border:1px dashed var(--pg-acid);animation:spin 5s linear infinite}.asset-controls{display:grid;gap:9px}.asset-controls header{display:flex;justify-content:space-between;gap:12px}.asset-controls header div{display:grid;gap:3px}.asset-controls strong{font-size:10px}.asset-controls small{color:var(--pg-muted);font:7px/1.4 var(--font-mono)}.asset-controls header button{border:0;background:none;color:#d88474;font:7px var(--font-mono);cursor:pointer}.asset-controls nav{display:flex;border-bottom:1px solid var(--pg-line)}.asset-controls nav button{border:0;border-bottom:2px solid transparent;background:none;color:var(--pg-muted);padding:7px 10px;font:7px var(--font-mono);cursor:pointer}.asset-controls nav button.active{border-color:var(--pg-acid);color:var(--pg-paper)}.upload-zone{position:relative;display:flex;align-items:center;justify-content:space-between;min-height:38px;padding:0 11px;border:1px dashed var(--pg-line);color:var(--pg-muted);font:8px var(--font-mono);cursor:pointer}.upload-zone input{position:absolute;inset:0;opacity:0;cursor:pointer}.upload-zone b{color:var(--pg-acid)}.generate-zone{display:grid;grid-template-columns:1fr auto;gap:7px}.generate-zone textarea{min-width:0;resize:vertical;border:1px solid var(--pg-line);background:#111412;color:var(--pg-paper);padding:9px;font:9px/1.5 var(--font-sans);outline:0}.generate-zone button{border:0;background:var(--pg-acid);color:#11130f;padding:0 12px;font:700 8px var(--font-mono);cursor:pointer}.generate-zone button:disabled{opacity:.35}.asset-controls>p{margin:0;color:#ff8a78;font:8px/1.4 var(--font-mono)}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:600px){.asset-picker,.asset-picker[data-kind=background]{grid-template-columns:72px 1fr}.asset-picker[data-kind=background] .asset-preview{aspect-ratio:1}.generate-zone{grid-template-columns:1fr}.generate-zone button{min-height:36px}}
</style>
