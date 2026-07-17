<script setup lang="ts">
import { computed } from 'vue'
import type { PlaygroundStateSettings } from '@/api/playground-types'


const props = defineProps<{ settings: PlaygroundStateSettings; snapshot: Record<string, unknown> }>()
const groups = computed(() => {
  const result = new Map<string, typeof props.settings.variables>()
  for (const variable of [...props.settings.variables].sort((a, b) => (a.order || 0) - (b.order || 0))) {
    const group = variable.group || '当前状态'
    result.set(group, [...(result.get(group) || []), variable])
  }
  return [...result.entries()]
})
function value(key: string) { return props.snapshot[key] }
function list(value: unknown) { return Array.isArray(value) ? value : value ? [String(value)] : [] }
function progress(variable: (typeof props.settings.variables)[number]) {
  const minimum = variable.minimum ?? 0
  const maximum = variable.maximum ?? 100
  const current = Number(value(variable.key) ?? minimum)
  return Math.max(0, Math.min(100, ((current - minimum) / (maximum - minimum)) * 100))
}
</script>

<template>
  <aside class="status-panel" :data-template="settings.template">
    <header><span>LIVE STATE</span><b>{{ settings.template === 'adventure' ? '冒险记录' : settings.template === 'nurturing' ? '养成面板' : settings.template === 'romance' ? '关系档案' : '状态栏' }}</b><i></i></header>
    <section v-for="([group, variables], groupIndex) in groups" :key="group">
      <h3><b>{{ String(groupIndex + 1).padStart(2, '0') }}</b>{{ group }}</h3>
      <div class="status-grid">
        <article v-for="variable in variables" :key="variable.key" :class="variable.type">
          <span>{{ variable.label }}</span>
          <template v-if="variable.type === 'progress'"><strong>{{ value(variable.key) ?? variable.initial_value ?? 0 }}</strong><i><b :style="{ width: `${progress(variable)}%` }"></b></i></template>
          <ul v-else-if="variable.type === 'list'"><li v-for="item in list(value(variable.key) ?? variable.initial_value)" :key="String(item)">{{ item }}</li><li v-if="!list(value(variable.key) ?? variable.initial_value).length">—</li></ul>
          <strong v-else>{{ value(variable.key) ?? variable.initial_value ?? '—' }}</strong>
        </article>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.status-panel{width:272px;max-height:calc(100vh - 115px);overflow:auto;padding:20px;border:1px solid rgba(255,255,255,.15);background:rgba(12,15,13,.78);color:#dce2dc;backdrop-filter:blur(18px);scrollbar-width:thin;scrollbar-color:#485049 transparent}.status-panel>header{display:grid;grid-template-columns:1fr auto;gap:6px;align-items:end;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,.13)}.status-panel>header span{color:var(--scene-acid);font:6px var(--font-mono);letter-spacing:.16em}.status-panel>header b{grid-row:2;font-size:14px}.status-panel>header i{grid-row:1/3;grid-column:2;width:30px;height:30px;border:1px solid rgba(215,255,63,.4);transform:rotate(45deg)}.status-panel section{padding:17px 0 5px;border-bottom:1px solid rgba(255,255,255,.08)}.status-panel h3{display:flex;gap:8px;margin:0 0 11px;color:#6d766f;font:7px var(--font-mono);font-weight:400}.status-panel h3 b{color:var(--scene-acid)}.status-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}.status-grid article{min-width:0;padding:9px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.025)}.status-grid article>span{display:block;overflow:hidden;text-overflow:ellipsis;color:#68716a;font:6px var(--font-mono);white-space:nowrap}.status-grid article>strong{display:block;margin-top:7px;overflow-wrap:anywhere;font-size:9px;font-weight:500}.status-grid article.progress{grid-column:1/-1;display:grid;grid-template-columns:1fr auto;align-items:center}.status-grid article.progress>strong{margin:0;color:var(--scene-acid);font:9px var(--font-mono)}.status-grid article.progress>i{grid-column:1/-1;height:2px;margin-top:9px;background:#303631}.status-grid article.progress>i b{display:block;height:100%;background:var(--scene-acid);transition:width .5s}.status-grid ul{grid-column:1/-1;margin:7px 0 0;padding:0;list-style:none}.status-grid li{padding:3px 0;color:#a8b0aa;font-size:8px}.status-panel[data-template=romance] {--scene-acid:#ff9da9}.status-panel[data-template=nurturing] {--scene-acid:#8fffe0}@media(max-width:1100px){.status-panel{width:auto;max-height:none}.status-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:650px){.status-grid{grid-template-columns:1fr 1fr}}
</style>
