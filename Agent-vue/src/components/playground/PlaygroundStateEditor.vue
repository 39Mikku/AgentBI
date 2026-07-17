<script setup lang="ts">
import type {
  PlaygroundStateSettings,
  PlaygroundStateTemplate,
  PlaygroundStateTemplates,
  PlaygroundStateVariable,
  PlaygroundStateVariableType,
} from '@/api/playground-types'


const props = defineProps<{
  modelValue: PlaygroundStateSettings
  templates: PlaygroundStateTemplates | null
}>()
const emit = defineEmits<{ 'update:modelValue': [value: PlaygroundStateSettings] }>()

function patch(fields: Partial<PlaygroundStateSettings>) {
  emit('update:modelValue', { ...props.modelValue, ...fields })
}

function changeTemplate(template: PlaygroundStateTemplate) {
  const variables = (props.templates?.[template] || []).map((item, index) => ({
    ...item,
    description: item.description || '',
    initial_value:
      item.initial_value ?? (item.type === 'progress' ? item.maximum ?? 100 : item.type === 'list' ? [] : ''),
    group: item.group || '',
    order: item.order ?? index * 10,
  }))
  patch({ template, variables })
}

function protectedKey(key: string) {
  return Boolean(props.templates?.[props.modelValue.template]?.some((item) => item.key === key))
}

function patchVariable(index: number, fields: Partial<PlaygroundStateVariable>) {
  patch({
    variables: props.modelValue.variables.map((item, i) =>
      i === index ? { ...item, ...fields } : item,
    ),
  })
}

function addVariable() {
  patch({
    variables: [
      ...props.modelValue.variables,
      {
        key: `custom_${props.modelValue.variables.length + 1}`,
        type: 'text',
        label: '自定义状态',
        description: '',
        initial_value: '',
        group: '',
        order: props.modelValue.variables.length * 10,
      },
    ],
  })
}

function removeVariable(index: number) {
  const variable = props.modelValue.variables[index]
  if (!variable || protectedKey(variable.key)) return
  patch({ variables: props.modelValue.variables.filter((_, i) => i !== index) })
}

function initialText(variable: PlaygroundStateVariable) {
  return Array.isArray(variable.initial_value)
    ? variable.initial_value.join(', ')
    : String(variable.initial_value ?? '')
}

function parseInitial(variable: PlaygroundStateVariable, value: string) {
  if (variable.type === 'progress') return Number(value)
  if (variable.type === 'list') return value.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean)
  return value
}
</script>

<template>
  <section class="state-editor editor-section">
    <header><div><span>06 / STATE PANEL</span><h3>状态栏</h3><p>模型每轮只更新变量值；键名、类型和布局由这里固定。</p></div><label class="switch"><input type="checkbox" :checked="modelValue.enabled" @change="patch({ enabled: ($event.target as HTMLInputElement).checked })" /><i></i><b>{{ modelValue.enabled ? '启用' : '停用' }}</b></label></header>
    <div class="state-config" :class="{ disabled: !modelValue.enabled }">
      <label><span>状态模板</span><select :value="modelValue.template" @change="changeTemplate(($event.target as HTMLSelectElement).value as PlaygroundStateTemplate)"><option value="adventure">冒险</option><option value="nurturing">养成</option><option value="romance">恋爱</option><option value="custom">空白自定义</option></select></label>
      <label><span>注入位置</span><select :value="modelValue.injection_position" @change="patch({ injection_position: ($event.target as HTMLSelectElement).value as PlaygroundStateSettings['injection_position'] })"><option value="system_start">系统提示词开头</option><option value="system_end">系统提示词末尾</option><option value="after_last_assistant">上一条回复后</option><option value="before_latest_user">最新用户输入前</option><option value="after_latest_user">最新用户输入后</option></select></label>
      <label class="wide"><span>自定义更新要求</span><textarea rows="3" :value="modelValue.update_instructions" placeholder="例如：关系值只有在角色明确建立信任时才上升，每轮最多变化 5 点。" @input="patch({ update_instructions: ($event.target as HTMLTextAreaElement).value })"></textarea></label>
    </div>
    <div class="variable-head"><div><strong>变量表</strong><small>预置变量锁定键名和类型，自定义变量可自由编辑。</small></div><button type="button" :disabled="!modelValue.enabled" @click="addVariable">＋ 自定义变量</button></div>
    <div class="variable-list" :class="{ disabled: !modelValue.enabled }">
      <article v-for="(variable, index) in modelValue.variables" :key="`${variable.key}-${index}`">
        <header><b>{{ String(index + 1).padStart(2, '0') }}</b><span v-if="protectedKey(variable.key)">PRESET</span><span v-else>CUSTOM</span><button v-if="!protectedKey(variable.key)" type="button" @click="removeVariable(index)">删除</button></header>
        <div class="variable-grid">
          <label><span>键名</span><input :disabled="protectedKey(variable.key)" :value="variable.key" @input="patchVariable(index, { key: ($event.target as HTMLInputElement).value })" /></label>
          <label><span>类型</span><select :disabled="protectedKey(variable.key)" :value="variable.type" @change="patchVariable(index, { type: ($event.target as HTMLSelectElement).value as PlaygroundStateVariableType })"><option value="text">文本</option><option value="progress">进度</option><option value="list">列表</option></select></label>
          <label><span>显示名称</span><input :value="variable.label" @input="patchVariable(index, { label: ($event.target as HTMLInputElement).value })" /></label>
          <label><span>初始值</span><input :type="variable.type === 'progress' ? 'number' : 'text'" :value="initialText(variable)" @input="patchVariable(index, { initial_value: parseInitial(variable, ($event.target as HTMLInputElement).value) })" /></label>
          <label v-if="variable.type === 'progress'"><span>最小值</span><input type="number" :value="variable.minimum ?? 0" @input="patchVariable(index, { minimum: Number(($event.target as HTMLInputElement).value) })" /></label>
          <label v-if="variable.type === 'progress'"><span>最大值</span><input type="number" :value="variable.maximum ?? 100" @input="patchVariable(index, { maximum: Number(($event.target as HTMLInputElement).value) })" /></label>
          <label><span>分组</span><input :value="variable.group || ''" @input="patchVariable(index, { group: ($event.target as HTMLInputElement).value })" /></label>
          <label><span>顺序</span><input type="number" :value="variable.order || 0" @input="patchVariable(index, { order: Number(($event.target as HTMLInputElement).value) })" /></label>
          <label class="wide"><span>变量说明</span><input :value="variable.description || ''" @input="patchVariable(index, { description: ($event.target as HTMLInputElement).value })" /></label>
        </div>
      </article>
      <div v-if="!modelValue.variables.length" class="empty">选择预置模板，或从空白模板添加自定义变量。</div>
    </div>
  </section>
</template>

<style scoped>
.editor-section{display:grid;gap:20px;padding:27px;border-top:1px solid var(--pg-line)}.state-editor>header{display:flex;justify-content:space-between;align-items:start;gap:20px}.state-editor header div>span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.14em}.state-editor h3{margin:8px 0 5px;font-size:18px}.state-editor header p{margin:0;color:var(--pg-muted);font-size:9px}.switch{display:flex;align-items:center;gap:8px;color:var(--pg-muted);font:7px var(--font-mono);cursor:pointer}.switch input{display:none}.switch i{position:relative;width:31px;height:16px;border:1px solid var(--pg-line);background:#101310}.switch i:after{content:'';position:absolute;width:8px;height:8px;left:3px;top:3px;background:#626963;transition:.2s}.switch input:checked+i{border-color:var(--pg-acid)}.switch input:checked+i:after{left:18px;background:var(--pg-acid)}.state-config{display:grid;grid-template-columns:1fr 1fr;gap:12px}.state-config.disabled,.variable-list.disabled{opacity:.35;pointer-events:none}.state-config label,.variable-grid label{display:grid;gap:6px}.state-config .wide,.variable-grid .wide{grid-column:1/-1}.state-config span,.variable-grid span{color:var(--pg-muted);font:7px var(--font-mono)}input,select,textarea{box-sizing:border-box;width:100%;border:1px solid var(--pg-line);outline:0;background:#0f1210;color:var(--pg-paper);padding:9px;font:9px var(--font-sans)}input,select{height:37px}select option{background:#151815}input:disabled,select:disabled{color:#6f7771;background:#151815}.variable-head{display:flex;justify-content:space-between;align-items:end;padding-top:18px;border-top:1px solid var(--pg-line)}.variable-head div{display:grid;gap:4px}.variable-head strong{font-size:12px}.variable-head small{color:var(--pg-muted);font:7px var(--font-mono)}.variable-head button{border:1px solid var(--pg-acid);background:none;color:var(--pg-acid);padding:8px 11px;font:7px var(--font-mono);cursor:pointer}.variable-list{display:grid;gap:8px}.variable-list article{display:grid;grid-template-columns:78px 1fr;border:1px solid var(--pg-line);background:#131614}.variable-list article>header{display:flex;flex-direction:column;align-items:start;gap:8px;padding:13px;border-right:1px solid var(--pg-line)}.variable-list article>header b{color:#58605a;font:12px var(--font-mono)}.variable-list article>header span{color:var(--pg-acid);font:6px var(--font-mono);letter-spacing:.12em}.variable-list article>header button{margin-top:auto;border:0;background:none;color:#c87769;padding:0;font:7px var(--font-mono);cursor:pointer}.variable-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:11px}.empty{padding:25px;border:1px dashed var(--pg-line);color:#606761;text-align:center;font:8px var(--font-mono)}@media(max-width:900px){.variable-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.editor-section{padding:20px}.state-editor>header{flex-direction:column}.state-config{grid-template-columns:1fr}.state-config .wide{grid-column:auto}.variable-head{align-items:start;flex-direction:column;gap:12px}.variable-list article{grid-template-columns:1fr}.variable-list article>header{flex-direction:row;align-items:center;border-right:0;border-bottom:1px solid var(--pg-line)}.variable-list article>header button{margin:0 0 0 auto}.variable-grid{grid-template-columns:1fr}.variable-grid .wide{grid-column:auto}}
</style>
