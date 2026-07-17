<script setup lang="ts">
import type { PlaygroundSummary } from '@/api/playground-types'


defineProps<{ summary: PlaygroundSummary }>()
const emit = defineEmits<{ view: []; edit: []; refresh: [] }>()
const labels = {
  idle: '已精炼此前内容', pending: '等待精炼', running: '正在后台精炼',
  failed: '上次精炼失败', stale: '分支已变化，等待重建',
}
</script>

<template>
  <div class="summary-marker" :data-status="summary.status">
    <i></i><div><span>CONTEXT CHECKPOINT</span><strong>{{ labels[summary.status] }}</strong></div><nav><button @click="emit('view')">查看总结</button><button @click="emit('edit')">编辑</button><button @click="emit('refresh')">重新生成</button></nav><i></i>
  </div>
</template>

<style scoped>
.summary-marker{display:grid;grid-template-columns:1fr auto auto 1fr;align-items:center;gap:13px;margin:32px -70px;color:#7f8881}.summary-marker>i{height:1px;background:linear-gradient(90deg,transparent,rgba(215,255,63,.34))}.summary-marker>i:last-child{background:linear-gradient(90deg,rgba(215,255,63,.34),transparent)}.summary-marker>div{display:grid;gap:3px;text-align:right}.summary-marker span{color:var(--scene-acid);font:6px var(--font-mono);letter-spacing:.14em}.summary-marker strong{font:8px var(--font-mono);font-weight:400}.summary-marker nav{display:flex;border:1px solid rgba(255,255,255,.13)}.summary-marker button{border:0;border-right:1px solid rgba(255,255,255,.1);background:rgba(12,15,13,.64);color:#788079;padding:8px;font:6px var(--font-mono);cursor:pointer}.summary-marker button:last-child{border:0}.summary-marker button:hover{color:var(--scene-acid)}.summary-marker[data-status=running] span{animation:pulse 1.2s ease-in-out infinite}.summary-marker[data-status=failed] span{color:#ff806c}@keyframes pulse{50%{opacity:.35}}@media(max-width:760px){.summary-marker{margin:25px 0;grid-template-columns:1fr}.summary-marker>i{display:none}.summary-marker>div{text-align:left}.summary-marker nav{width:max-content}}
</style>
