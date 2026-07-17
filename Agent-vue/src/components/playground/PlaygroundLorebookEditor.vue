<script setup lang="ts">
import type {
  PlaygroundContextEntry,
  PlaygroundPromptSlot,
} from '@/api/playground-types'


const props = defineProps<{ modelValue: PlaygroundContextEntry[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: PlaygroundContextEntry[]] }>()
const slots: Array<{ value: PlaygroundPromptSlot; label: string }> = [
  { value: 'system_start', label: '系统提示词开头' },
  { value: 'system_end', label: '系统提示词末尾' },
  { value: 'after_last_assistant', label: '上一条回复后' },
  { value: 'before_latest_user', label: '最新用户输入前' },
  { value: 'after_latest_user', label: '最新用户输入后' },
]

function add() {
  emit('update:modelValue', [
    ...props.modelValue,
    {
      name: '新世界书条目', category: '', content: '', enabled: true,
      activation_mode: 'constant', keywords: [], scan_depth: 8,
      injection_position: 'system_end', priority: 0,
    },
  ])
}
function patch(index: number, fields: Partial<PlaygroundContextEntry>) {
  emit('update:modelValue', props.modelValue.map((item, i) => i === index ? { ...item, ...fields } : item))
}
function remove(index: number) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index))
}
function keywords(value: string) {
  return value.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean)
}
</script>

<template>
  <section class="lorebook editor-section">
    <header><div><span>04 / LOREBOOK</span><h3>世界书</h3><p>常驻条目始终注入；关键词条目扫描最近消息。所有命中项都会保留。</p></div><button type="button" @click="add">＋ 新增条目</button></header>
    <div class="entry-list">
      <article v-for="(entry, index) in modelValue" :key="entry.id || index">
        <div class="entry-title"><b>{{ String(index + 1).padStart(2, '0') }}</b><input :value="entry.name" @input="patch(index, { name: ($event.target as HTMLInputElement).value })" /><input class="category" :value="entry.category" placeholder="分类" @input="patch(index, { category: ($event.target as HTMLInputElement).value })" /><label><input type="checkbox" :checked="entry.enabled" @change="patch(index, { enabled: ($event.target as HTMLInputElement).checked })" />启用</label><button type="button" @click="remove(index)">删除</button></div>
        <textarea rows="5" :value="entry.content" placeholder="写入人物、地点、规则或世界事实…" @input="patch(index, { content: ($event.target as HTMLTextAreaElement).value })"></textarea>
        <div class="entry-controls">
          <label><span>触发方式</span><select :value="entry.activation_mode" @change="patch(index, { activation_mode: ($event.target as HTMLSelectElement).value as PlaygroundContextEntry['activation_mode'] })"><option value="constant">常驻</option><option value="keyword">关键词</option></select></label>
          <label v-if="entry.activation_mode === 'keyword'" class="keyword"><span>关键词（逗号分隔）</span><input :value="entry.keywords.join(', ')" @input="patch(index, { keywords: keywords(($event.target as HTMLInputElement).value) })" /></label>
          <label v-if="entry.activation_mode === 'keyword'"><span>扫描消息数</span><input type="number" min="1" max="200" :value="entry.scan_depth" @input="patch(index, { scan_depth: Number(($event.target as HTMLInputElement).value) })" /></label>
          <label><span>注入位置</span><select :value="entry.injection_position" @change="patch(index, { injection_position: ($event.target as HTMLSelectElement).value as PlaygroundPromptSlot })"><option v-for="slot in slots" :key="slot.value" :value="slot.value">{{ slot.label }}</option></select></label>
          <label><span>优先级</span><input type="number" :value="entry.priority" @input="patch(index, { priority: Number(($event.target as HTMLInputElement).value) })" /></label>
        </div>
      </article>
      <div v-if="!modelValue.length" class="empty">世界书尚为空。角色和世界仍可只依赖主提示词运行。</div>
    </div>
  </section>
</template>

<style scoped>
.editor-section{display:grid;gap:20px;padding:27px;border-top:1px solid var(--pg-line)}.lorebook>header{display:flex;justify-content:space-between;align-items:start;gap:20px}.lorebook header span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.14em}.lorebook h3{margin:8px 0 5px;font-size:18px}.lorebook header p{margin:0;color:var(--pg-muted);font-size:9px}.lorebook header button{border:1px solid var(--pg-acid);background:transparent;color:var(--pg-acid);padding:9px 12px;font:8px var(--font-mono);cursor:pointer}.entry-list{display:grid;gap:10px}.entry-list article{border:1px solid var(--pg-line);background:#131614}.entry-title{display:grid;grid-template-columns:30px minmax(130px,1fr) 120px auto auto;gap:8px;align-items:center;padding:9px;border-bottom:1px solid var(--pg-line)}.entry-title>b{color:#59615b;font:8px var(--font-mono)}input,select,textarea{box-sizing:border-box;width:100%;border:1px solid var(--pg-line);outline:0;background:#0f1210;color:var(--pg-paper);padding:9px;font:9px var(--font-sans)}input,select{height:35px}select option{background:#151815}.entry-title>input{border:0;background:transparent;font-weight:700}.entry-title .category{border-left:1px solid var(--pg-line);font-weight:400}.entry-title label{display:flex;gap:5px;color:var(--pg-muted);font:7px var(--font-mono)}.entry-title label input{width:auto;height:auto;accent-color:var(--pg-acid)}.entry-title button{border:0;background:none;color:#ca7769;font:7px var(--font-mono);cursor:pointer}.entry-list article>textarea{border:0;resize:vertical}.entry-controls{display:grid;grid-template-columns:120px minmax(150px,1fr) 100px minmax(150px,1fr) 90px;gap:8px;padding:10px;border-top:1px solid var(--pg-line)}.entry-controls label{display:grid;gap:5px}.entry-controls span{color:var(--pg-muted);font:7px var(--font-mono)}.empty{padding:30px;border:1px dashed var(--pg-line);color:#606761;text-align:center;font:8px var(--font-mono)}@media(max-width:900px){.entry-controls{grid-template-columns:repeat(2,1fr)}.entry-title{grid-template-columns:25px 1fr auto auto}.entry-title .category{grid-row:2;grid-column:2/-1}}@media(max-width:600px){.editor-section{padding:20px}.lorebook>header{flex-direction:column}.entry-controls{grid-template-columns:1fr}.entry-title{grid-template-columns:20px 1fr auto}.entry-title label{display:none}.entry-title button{grid-column:3}.entry-title .category{grid-column:2/-1}}
</style>
