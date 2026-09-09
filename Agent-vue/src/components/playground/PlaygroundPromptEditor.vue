<script setup lang="ts">
import type {
  PlaygroundPersona,
  PlaygroundPromptModule,
  PlaygroundPromptSlot,
} from '@/api/playground-types'


const props = defineProps<{
  persona: PlaygroundPersona
  modules: PlaygroundPromptModule[]
}>()
const emit = defineEmits<{
  'update:persona': [value: PlaygroundPersona]
  'update:modules': [value: PlaygroundPromptModule[]]
}>()
const slots: Array<{ value: PlaygroundPromptSlot; label: string }> = [
  { value: 'system_start', label: '系统提示词开头' },
  { value: 'system_end', label: '系统提示词末尾' },
  { value: 'after_last_assistant', label: '上一条回复后' },
  { value: 'before_latest_user', label: '最新用户输入前' },
  { value: 'after_latest_user', label: '最新用户输入后' },
]

function patchPersona(fields: Partial<PlaygroundPersona>) {
  emit('update:persona', { ...props.persona, ...fields })
}

function addModule() {
  emit('update:modules', [
    ...props.modules,
    {
      name: '新提示词模块',
      content: '',
      enabled: true,
      injection_position: 'system_end',
      sort_order: props.modules.length * 10,
    },
  ])
}

function patchModule(index: number, fields: Partial<PlaygroundPromptModule>) {
  emit(
    'update:modules',
    props.modules.map((item, itemIndex) =>
      itemIndex === index ? { ...item, ...fields } : item,
    ),
  )
}

function removeModule(index: number) {
  emit('update:modules', props.modules.filter((_, itemIndex) => itemIndex !== index))
}
</script>

<template>
  <section class="prompt-editor editor-section">
    <header class="section-head"><div><span>02 / USER PERSONA</span><h3>用户人设</h3><p>它与角色设定、世界书和大总结同级，不写入普通消息。</p></div><label class="switch"><input type="checkbox" :checked="persona.enabled" @change="patchPersona({ enabled: ($event.target as HTMLInputElement).checked })" /><i></i><b>{{ persona.enabled ? '启用' : '停用' }}</b></label></header>
    <div class="persona-grid" :class="{ disabled: !persona.enabled }">
      <label><span>称呼 / 名称</span><input :value="persona.name" @input="patchPersona({ name: ($event.target as HTMLInputElement).value })" /></label>
      <label><span>注入位置</span><select :value="persona.injection_position" @change="patchPersona({ injection_position: ($event.target as HTMLSelectElement).value as PlaygroundPromptSlot })"><option v-for="slot in slots" :key="slot.value" :value="slot.value">{{ slot.label }}</option></select></label>
      <label class="wide"><span>身份</span><textarea rows="3" :value="persona.identity_text" @input="patchPersona({ identity_text: ($event.target as HTMLTextAreaElement).value })"></textarea></label>
      <label><span>背景</span><textarea rows="4" :value="persona.background" @input="patchPersona({ background: ($event.target as HTMLTextAreaElement).value })"></textarea></label>
      <label><span>性格</span><textarea rows="4" :value="persona.personality" @input="patchPersona({ personality: ($event.target as HTMLTextAreaElement).value })"></textarea></label>
      <label class="wide"><span>与角色 / 世界的初始关系</span><textarea rows="3" :value="persona.initial_relationship" @input="patchPersona({ initial_relationship: ($event.target as HTMLTextAreaElement).value })"></textarea></label>
    </div>
    <div class="module-divider"><div><span>03 / PROMPT MODULES</span><h3>提示词模块</h3></div><button type="button" @click="addModule">＋ 新增模块</button></div>
    <div v-if="modules.length" class="module-list">
      <article v-for="(module, index) in modules" :key="module.id || index" class="module-card">
        <header><b>{{ String(index + 1).padStart(2, '0') }}</b><input :value="module.name" @input="patchModule(index, { name: ($event.target as HTMLInputElement).value })" /><label class="mini-switch"><input type="checkbox" :checked="module.enabled" @change="patchModule(index, { enabled: ($event.target as HTMLInputElement).checked })" /><i></i></label><button type="button" @click="removeModule(index)">删除</button></header>
        <textarea rows="5" :value="module.content" placeholder="写入这个模块的提示词内容…" @input="patchModule(index, { content: ($event.target as HTMLTextAreaElement).value })"></textarea>
        <footer><label><span>注入位置</span><select :value="module.injection_position" @change="patchModule(index, { injection_position: ($event.target as HTMLSelectElement).value as PlaygroundPromptSlot })"><option v-for="slot in slots" :key="slot.value" :value="slot.value">{{ slot.label }}</option></select></label><label><span>顺序</span><input type="number" :value="module.sort_order" @input="patchModule(index, { sort_order: Number(($event.target as HTMLInputElement).value) })" /></label></footer>
      </article>
    </div>
    <div v-else class="empty-line">尚未添加额外提示词模块。主提示词仍会正常生效。</div>
  </section>
</template>

<style scoped>
.editor-section{display:grid;gap:20px;padding:27px;border-top:1px solid var(--pg-line)}.section-head,.module-divider{display:flex;align-items:start;justify-content:space-between;gap:20px}.section-head span,.module-divider span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.14em}.section-head h3,.module-divider h3{margin:8px 0 5px;font-size:18px;letter-spacing:-.04em}.section-head p{margin:0;color:var(--pg-muted);font-size:9px}.switch{display:flex;align-items:center;gap:8px;color:var(--pg-muted);font:var(--control-font-size) var(--font-mono);cursor:pointer}.switch input,.mini-switch input{display:none}.switch i,.mini-switch i{position:relative;width:31px;height:16px;border:1px solid var(--pg-line);background:#101310}.switch i:after,.mini-switch i:after{content:'';position:absolute;width:8px;height:8px;left:3px;top:3px;background:#626963;transition:.2s}.switch input:checked+i,.mini-switch input:checked+i{border-color:var(--pg-acid)}.switch input:checked+i:after,.mini-switch input:checked+i:after{left:18px;background:var(--pg-acid)}.persona-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px;transition:opacity .2s}.persona-grid.disabled{opacity:.35;pointer-events:none}.persona-grid label,.module-card footer label{display:grid;gap:6px}.persona-grid .wide{grid-column:1/-1}.persona-grid label>span,.module-card footer span{color:var(--pg-muted);font:7px var(--font-mono)}input,select,textarea{width:100%;box-sizing:border-box;border:1px solid var(--pg-line);outline:0;background:#101310;color:var(--pg-paper);padding:10px;font:var(--control-font-size)/1.55 var(--font-sans)}select,input{height:39px}select option{background:#151815}.module-divider{padding-top:22px;border-top:1px solid var(--pg-line)}.module-divider button{border:1px solid var(--pg-acid);background:transparent;color:var(--pg-acid);padding:9px 12px;font:var(--control-font-size) var(--font-mono);cursor:pointer}.module-list{display:grid;gap:10px}.module-card{border:1px solid var(--pg-line);background:#131614}.module-card>header{display:grid;grid-template-columns:32px 1fr auto auto;align-items:center;gap:8px;padding:9px;border-bottom:1px solid var(--pg-line)}.module-card>header>b{color:#5b635d;font:8px var(--font-mono)}.module-card>header input{height:31px;border:0;background:transparent;padding:5px;font-weight:700}.mini-switch i{display:block;width:27px;height:14px}.mini-switch i:after{width:7px;height:7px;top:2px}.mini-switch input:checked+i:after{left:16px}.module-card>header button{border:0;background:none;color:#c97769;font:var(--control-font-size) var(--font-mono);cursor:pointer}.module-card>textarea{border:0;resize:vertical;background:#101310}.module-card footer{display:grid;grid-template-columns:1fr 100px;gap:10px;padding:10px;border-top:1px solid var(--pg-line)}.module-card footer input,.module-card footer select{height:34px}.empty-line{padding:28px;border:1px dashed var(--pg-line);color:#5f665f;text-align:center;font:8px var(--font-mono)}@media(max-width:700px){.editor-section{padding:20px}.section-head,.module-divider{align-items:stretch;flex-direction:column}.persona-grid{grid-template-columns:1fr}.persona-grid .wide{grid-column:auto}}
</style>
