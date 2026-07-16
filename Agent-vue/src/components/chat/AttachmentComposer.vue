<script setup lang="ts">
import { ref } from 'vue'
import { deleteAsset, uploadAsset } from '@/api/studio-assets'
import type { StudioAsset } from '@/api/chat-types'
import { assetContentUrl, formatAssetSize, validateAttachmentBatch } from '@/utils/chat-attachments'

const props = defineProps<{ userId: string; modelValue: StudioAsset[]; disabled?: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: StudioAsset[]]
  busy: [value: boolean]
}>()
const input = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const error = ref('')

async function selectFiles(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  ;(event.target as HTMLInputElement).value = ''
  const combined = [
    ...props.modelValue.map((asset) => ({
      name: asset.filename,
      size: asset.size,
      type: asset.mime_type,
    })),
    ...files,
  ]
  const invalid = validateAttachmentBatch(combined)
  if (invalid) {
    error.value = invalid
    return
  }
  if (!files.length) return
  error.value = ''
  uploading.value = true
  emit('busy', true)
  try {
    const uploaded = await Promise.all(files.map((file) => uploadAsset(props.userId, file)))
    emit('update:modelValue', [...props.modelValue, ...uploaded])
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '附件上传失败'
  } finally {
    uploading.value = false
    emit('busy', false)
  }
}

async function remove(asset: StudioAsset) {
  emit('update:modelValue', props.modelValue.filter((item) => item.id !== asset.id))
  try {
    await deleteAsset(props.userId, asset.id)
  } catch {
    // The unbound upload will also be removed by server-side orphan cleanup.
  }
}
</script>

<template>
  <div class="attachment-composer">
    <input
      ref="input"
      hidden
      type="file"
      multiple
      accept="image/png,image/jpeg,image/webp,image/gif,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      @change="selectFiles"
    />
    <div v-if="modelValue.length" class="pending-assets">
      <article v-for="asset in modelValue" :key="asset.id">
        <img
          v-if="asset.kind === 'image'"
          :src="assetContentUrl(asset.id, userId)"
          :alt="asset.filename"
        />
        <span v-else class="doc-mark">DOC<br />X</span>
        <div><strong>{{ asset.filename }}</strong><small>{{ formatAssetSize(asset.size) }}</small></div>
        <button type="button" title="移除附件" @click="remove(asset)">×</button>
      </article>
    </div>
    <div class="attachment-controls">
      <button
        type="button"
        class="attach-button"
        :disabled="disabled || uploading"
        @click="input?.click()"
      >
        <b>{{ uploading ? '···' : '+' }}</b><span>{{ uploading ? '正在上传' : '图片 / DOCX' }}</span>
      </button>
      <p v-if="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.attachment-composer{display:grid;gap:8px}.pending-assets{display:flex;gap:7px;overflow-x:auto;padding:2px 1px}.pending-assets article{flex:0 0 188px;min-width:0;height:54px;display:grid;grid-template-columns:42px minmax(0,1fr) 23px;align-items:center;gap:8px;padding:5px;border:1px solid #d3d0c7;background:#f1efe8}.pending-assets img,.doc-mark{width:42px;height:42px;object-fit:cover;background:#181818;color:#d9ff36}.doc-mark{display:grid;place-items:center;text-align:center;font:700 8px/1 'DM Mono'}.pending-assets div{min-width:0}.pending-assets strong,.pending-assets small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.pending-assets strong{font-size:9px}.pending-assets small{margin-top:5px;color:#88847b;font:7px 'DM Mono'}.pending-assets article>button{border:0;background:transparent;color:#777;font-size:16px;cursor:pointer}.attachment-controls{display:flex;align-items:center;gap:10px}.attach-button{display:flex;align-items:center;gap:7px;border:0;background:transparent;color:#65625b;padding:3px 0;font:8px 'DM Mono';cursor:pointer}.attach-button:hover{color:#111}.attach-button b{display:grid;width:20px;height:20px;place-items:center;border:1px solid #aaa69d;border-radius:50%;font:14px Manrope}.attachment-controls p{margin:0;color:#c14b3e;font:8px 'DM Mono'}
</style>
