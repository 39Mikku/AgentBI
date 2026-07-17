<script setup lang="ts">
defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    class="rail-toggle"
    type="button"
    :title="collapsed ? '展开侧栏' : '收起侧栏'"
    :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
    :aria-expanded="!collapsed"
    @click="$emit('toggle')"
  >
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="m12.5 5-5 5 5 5" />
    </svg>
  </button>
</template>

<style scoped>
.rail-toggle{position:absolute;z-index:8;right:-14px;top:75px;width:28px;height:28px;display:grid;place-items:center;border:1px solid color-mix(in srgb,currentColor 28%,transparent);border-radius:50%;background:#171717;color:#d9ff36;box-shadow:0 6px 18px rgba(0,0,0,.28);cursor:pointer;transition:transform .22s ease,background .18s ease,color .18s ease}.rail-toggle:hover{background:#d9ff36;color:#111}.rail-toggle svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}.rail-toggle[aria-expanded='false'] svg{transform:rotate(180deg)}.rail-toggle:focus-visible{outline:2px solid currentColor;outline-offset:2px}@media(max-width:820px){.rail-toggle{display:none}}@media(prefers-reduced-motion:reduce){.rail-toggle{transition:none}}
</style>
