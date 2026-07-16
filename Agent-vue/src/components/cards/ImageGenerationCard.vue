<script setup lang="ts">
defineProps<{
  url?: string
  prompt?: string
  mode?: string
  model?: string
  aspectRatio?: string
  width?: number | null
  height?: number | null
  deleted?: boolean
}>()
</script>

<template>
  <figure class="image-card">
    <div v-if="deleted" class="image-stage deleted-stage">
      <b>×</b><span>生成图片已删除</span>
    </div>
    <a v-else class="image-stage" :href="url" target="_blank" rel="noopener noreferrer">
      <img :src="url" :alt="prompt || 'AI 生成图片'" loading="lazy" />
      <span>查看原图 ↗</span>
    </a>
    <figcaption>
      <div>
        <small>GENERATED IMAGE / {{ (mode || 'lite').toUpperCase() }}</small>
        <strong>{{ model || 'IMAGE MODEL' }}</strong>
      </div>
      <p v-if="prompt">{{ prompt }}</p>
      <footer>
        <span>{{ aspectRatio || 'square' }}<template v-if="width && height"> · {{ width }}×{{ height }}</template></span>
        <a v-if="!deleted" :href="url" download>下载 PNG ↓</a><span v-else>FILE REMOVED</span>
      </footer>
    </figcaption>
  </figure>
</template>

<style scoped>
.image-card{max-width:min(760px,100%);margin:14px 0 20px;border:1px solid rgba(17,17,17,.18);background:#f7f5ef;box-shadow:7px 7px 0 rgba(17,17,17,.08);overflow:hidden}.image-stage{position:relative;display:block;min-height:220px;max-height:620px;overflow:hidden;background:#171717}.image-stage img{display:block;width:100%;max-height:620px;object-fit:contain}.image-stage>span{position:absolute;right:12px;bottom:12px;padding:7px 9px;background:rgba(17,17,17,.82);color:#d9ff36;font:8px 'DM Mono';letter-spacing:.06em;opacity:0;transform:translateY(4px);transition:.18s}.image-stage:hover>span{opacity:1;transform:none}.image-card figcaption{padding:15px 17px 13px}.image-card figcaption>div{display:flex;justify-content:space-between;gap:15px}.image-card small{color:#79766e;font:7px 'DM Mono';letter-spacing:.13em}.image-card strong{font:700 9px 'DM Mono';letter-spacing:.04em}.image-card p{display:-webkit-box;margin:11px 0;color:#66625a;font:10px/1.55 Manrope;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2}.image-card footer{display:flex;justify-content:space-between;padding-top:10px;border-top:1px solid rgba(17,17,17,.12);color:#88847c;font:7px 'DM Mono'}.image-card footer a{color:#171717;text-decoration:none}.image-card footer a:hover{color:#708600}
.deleted-stage{display:grid;place-content:center;justify-items:center;color:#777}.deleted-stage b{font:300 54px Manrope}.deleted-stage>span{position:static;margin-top:8px;padding:0;background:transparent;color:#8d8981;opacity:1;transform:none;font:8px 'DM Mono'}
</style>
