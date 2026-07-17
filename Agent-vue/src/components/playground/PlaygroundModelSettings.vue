<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { listProviders } from '@/api/providers'
import type { ProviderProfile } from '@/api/chat-types'
import type { PlaygroundPreferences } from '@/api/playground-types'


const props = defineProps<{ modelValue: PlaygroundPreferences; saving?: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: PlaygroundPreferences]
  save: []
}>()
const providers = ref<ProviderProfile[]>([])
const selectedProvider = computed(() =>
  providers.value.find((item) => item.id === props.modelValue.providerId),
)
const selectedSummaryProvider = computed(() =>
  providers.value.find((item) => item.id === props.modelValue.summaryProviderId),
)

function patch(fields: Partial<PlaygroundPreferences>) {
  emit('update:modelValue', { ...props.modelValue, ...fields })
}

function changeProvider(providerId: string) {
  const provider = providers.value.find((item) => item.id === providerId)
  patch({ providerId: providerId || undefined, model: provider?.default_model || undefined })
}

function changeSummaryProvider(providerId: string) {
  const provider = providers.value.find((item) => item.id === providerId)
  patch({
    summaryProviderId: providerId || undefined,
    summaryModel: provider?.default_model || undefined,
  })
}

onMounted(async () => {
  providers.value = await listProviders()
})
</script>

<template>
  <section class="model-settings">
    <header><span>PLAYGROUND / MODEL</span><h2>公共模型设置</h2><p>这里的聊天模型对所有角色与世界生效；资料页只允许覆盖大总结模型。</p></header>
    <div class="settings-grid">
      <label><span>聊天提供商</span><select :value="modelValue.providerId || ''" @change="changeProvider(($event.target as HTMLSelectElement).value)"><option value="">选择提供商</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option></select></label>
      <label><span>聊天模型</span><select :value="modelValue.model || ''" @change="patch({ model: ($event.target as HTMLSelectElement).value || undefined })"><option value="">选择模型</option><option v-for="model in selectedProvider?.available_models || []" :key="model" :value="model">{{ model }}</option></select></label>
      <label><span>温度 <b>{{ modelValue.temperature.toFixed(1) }}</b></span><input type="range" min="0" max="2" step="0.1" :value="modelValue.temperature" @input="patch({ temperature: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label><span>上下文轮数 <b>{{ modelValue.contextTurns === 0 ? '不截断' : modelValue.contextTurns }}</b></span><input type="range" min="0" max="100" step="2" :value="modelValue.contextTurns" @input="patch({ contextTurns: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label><span>推理强度</span><select :value="modelValue.thinkingLevel" @change="patch({ thinkingLevel: ($event.target as HTMLSelectElement).value as PlaygroundPreferences['thinkingLevel'] })"><option value="off">关闭</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option></select></label>
    </div>
    <div class="summary-grid">
      <div class="summary-copy"><span>LONG CONTEXT</span><strong>大总结默认值</strong><p>达到阈值后在后台更新一份会话级精炼记录，原始消息不会删除。</p></div>
      <label><span>总结提供商</span><select :value="modelValue.summaryProviderId || ''" @change="changeSummaryProvider(($event.target as HTMLSelectElement).value)"><option value="">跟随聊天模型</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option></select></label>
      <label><span>总结模型</span><select :value="modelValue.summaryModel || ''" @change="patch({ summaryModel: ($event.target as HTMLSelectElement).value || undefined })"><option value="">跟随聊天模型</option><option v-for="model in selectedSummaryProvider?.available_models || []" :key="model" :value="model">{{ model }}</option></select></label>
      <label><span>触发新消息数</span><input type="number" min="4" max="500" :value="modelValue.summaryTriggerMessages" @input="patch({ summaryTriggerMessages: Number(($event.target as HTMLInputElement).value) })" /></label>
      <label><span>总结后保留消息</span><input type="number" min="2" max="100" :value="modelValue.summaryRetainMessages" @input="patch({ summaryRetainMessages: Number(($event.target as HTMLInputElement).value) })" /></label>
    </div>
    <button class="save-model" type="button" :disabled="saving" @click="emit('save')">{{ saving ? '保存中…' : '保存公共设置' }} <b>↗</b></button>
  </section>
</template>

<style scoped>
.model-settings{display:grid;gap:25px;padding:28px;border:1px solid var(--pg-line);background:#171a18}.model-settings header span,.summary-copy span{color:var(--pg-acid);font:7px var(--font-mono);letter-spacing:.16em}.model-settings h2{margin:10px 0 6px;font:600 24px/1 var(--font-display);letter-spacing:-.05em}.model-settings header p,.summary-copy p{margin:0;color:var(--pg-muted);font-size:9px;line-height:1.6}.settings-grid,.summary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.summary-grid{padding-top:22px;border-top:1px solid var(--pg-line)}.summary-copy{grid-column:1/-1}.summary-copy strong{display:block;margin-top:8px;font-size:13px}.model-settings label{display:grid;gap:7px}.model-settings label>span{display:flex;justify-content:space-between;color:#929a94;font:7px var(--font-mono);letter-spacing:.07em}.model-settings label b{color:var(--pg-acid)}.model-settings select,.model-settings input[type=number]{width:100%;height:39px;border:1px solid var(--pg-line);outline:0;background:#0f1210;color:#e8ece8;padding:0 10px;font:9px var(--font-mono)}.model-settings select option{background:#131614;color:#ecefe9}.model-settings input[type=range]{width:100%;height:2px;margin:17px 0 12px;appearance:none;background:#3c443f;accent-color:var(--pg-acid)}.model-settings input[type=range]::-webkit-slider-thumb{appearance:none;width:12px;height:12px;border:3px solid #171a18;background:var(--pg-acid);box-shadow:0 0 0 1px var(--pg-acid)}.save-model{justify-self:end;min-width:190px;height:44px;border:1px solid var(--pg-acid);background:var(--pg-acid);color:#11130f;padding:0 14px;text-align:left;font:700 8px var(--font-mono);cursor:pointer}.save-model b{float:right;font-size:14px}.save-model:disabled{opacity:.4}@media(max-width:700px){.settings-grid,.summary-grid{grid-template-columns:1fr}.save-model{justify-self:stretch}}
</style>
