<script setup lang="ts">
import { ref, watch } from 'vue'


const props = defineProps<{ options: Array<{ text: string }>; disabled?: boolean }>()
const emit = defineEmits<{ select: [text: string] }>()
const chosen = ref(false)
watch(() => props.options, () => { chosen.value = false })
function choose(text: string) {
  if (chosen.value || props.disabled) return
  chosen.value = true
  emit('select', text)
}
</script>

<template>
  <div class="action-options">
    <div class="option-rule"><span>WHAT HAPPENS NEXT</span><i></i></div>
    <button v-for="(option, index) in options" :key="`${index}-${option.text}`" :disabled="chosen || disabled" @click="choose(option.text)"><b>{{ String(index + 1).padStart(2, '0') }}</b><span>{{ option.text }}</span><i>↗</i></button>
  </div>
</template>

<style scoped>
.action-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:27px 0 12px}.option-rule{grid-column:1/-1;display:flex;align-items:center;gap:12px;margin-bottom:3px}.option-rule span{color:rgba(232,236,231,.48);font:7px var(--font-mono);letter-spacing:.16em}.option-rule i{height:1px;flex:1;background:rgba(255,255,255,.14)}.action-options button{display:grid;grid-template-columns:27px 1fr auto;align-items:center;gap:9px;min-height:48px;border:1px solid rgba(255,255,255,.16);background:rgba(13,16,14,.68);color:#dce2dc;padding:10px;text-align:left;backdrop-filter:blur(12px);cursor:pointer;transition:.2s}.action-options button:hover{border-color:var(--scene-acid);background:rgba(24,29,25,.9);transform:translateY(-1px)}.action-options button b{color:var(--scene-acid);font:7px var(--font-mono)}.action-options button span{font-size:9px;line-height:1.45}.action-options button i{color:#6f7771;font-style:normal}.action-options button:disabled{opacity:.35;transform:none;cursor:default}@media(max-width:650px){.action-options{grid-template-columns:1fr}}
</style>
