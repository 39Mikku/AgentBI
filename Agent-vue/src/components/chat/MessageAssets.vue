<script setup lang="ts">
import type { StudioAsset } from '@/api/chat-types'
import { assetContentUrl, formatAssetSize } from '@/utils/chat-attachments'

defineProps<{ assets: StudioAsset[]; userId: string }>()
</script>

<template>
  <div v-if="assets.length" class="message-assets">
    <template v-for="asset in assets" :key="asset.id">
      <article v-if="asset.status === 'deleted' || asset.deleted_at" class="asset-deleted">
        <span>×</span><div><strong>{{ asset.filename }}</strong><small>附件已删除</small></div>
      </article>
      <a
        v-else-if="asset.kind === 'image'"
        class="image-asset"
        :href="assetContentUrl(asset.id, userId)"
        target="_blank"
        rel="noreferrer"
      >
        <img :src="assetContentUrl(asset.id, userId)" :alt="asset.filename" />
        <span>{{ asset.source === 'generated' ? 'AI 生成' : asset.filename }}</span>
      </a>
      <a
        v-else-if="asset.kind === 'video'"
        class="video-asset"
        :href="assetContentUrl(asset.id, userId)"
        target="_blank"
        rel="noreferrer"
      >
        <video :src="assetContentUrl(asset.id, userId)" muted preload="metadata"></video>
        <span>AI 视频 · 点击播放</span>
      </a>
      <a
        v-else
        class="doc-asset"
        :href="assetContentUrl(asset.id, userId)"
        download
      >
        <b>DOCX</b><div><strong>{{ asset.filename }}</strong><small>{{ formatAssetSize(asset.size) }}</small></div><i>↓</i>
      </a>
    </template>
  </div>
</template>

<style scoped>
.message-assets{display:flex;flex-wrap:wrap;gap:8px;margin:7px 0 11px}.image-asset{position:relative;display:block;width:min(210px,100%);overflow:hidden;border:1px solid #ccc8bd;background:#dedbd3;color:#fff}.image-asset img{display:block;width:100%;max-height:240px;object-fit:cover}.image-asset span{position:absolute;left:7px;bottom:7px;max-width:calc(100% - 14px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:4px 6px;background:rgba(0,0,0,.7);font:7px 'DM Mono'}.doc-asset,.asset-deleted{min-width:220px;max-width:360px;display:grid;grid-template-columns:42px minmax(0,1fr) auto;align-items:center;gap:10px;padding:9px;border:1px solid #c9c6bd;background:rgba(255,255,255,.3);color:#222;text-decoration:none}.doc-asset>b,.asset-deleted>span{display:grid;width:42px;height:42px;place-items:center;background:#161616;color:#d9ff36;font:7px 'DM Mono'}.doc-asset strong,.doc-asset small,.asset-deleted strong,.asset-deleted small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.doc-asset strong,.asset-deleted strong{font-size:10px}.doc-asset small,.asset-deleted small{margin-top:4px;color:#777;font:7px 'DM Mono'}.doc-asset i{font-style:normal;font-size:17px}.asset-deleted{opacity:.55}.asset-deleted>span{color:#b4b0a5;background:#333}
</style>
<style scoped>
.video-asset{position:relative;display:block;width:min(310px,100%);overflow:hidden;border:1px solid #ccc8bd;background:#171717;color:#fff}.video-asset video{display:block;width:100%;max-height:240px;object-fit:cover}.video-asset span{position:absolute;left:7px;bottom:7px;max-width:calc(100% - 14px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:4px 6px;background:rgba(0,0,0,.7);font:7px 'DM Mono'}
</style>
