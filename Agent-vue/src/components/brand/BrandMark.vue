<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: 'default' | 'inverse' | 'light' | 'dark'
    label?: string
  }>(),
  { tone: 'default', label: 'AgentBI' },
)
</script>

<template>
  <svg class="brand-mark" :class="`tone-${tone}`" viewBox="0 0 256 256" role="img" :aria-label="label">
    <path class="brand-mark__stem" d="M24 220 116 32v140l-36 48H24Z" />
    <path class="brand-mark__cells" d="M136 38h57c24 0 43 18 43 41s-19 41-43 41h-57V38Zm0 100h57c24 0 43 18 43 41s-19 41-43 41h-57v-82Z" />
  </svg>
</template>

<style scoped>
.brand-mark { display:block; width:100%; height:100%; overflow:visible; }
.brand-mark__stem { fill:#11110f; }
.brand-mark__cells { fill:#d9ff36; }
.tone-inverse .brand-mark__stem { fill:#efede6; }
.tone-inverse .brand-mark__cells { fill:#d9ff36; }
.tone-light .brand-mark__stem,.tone-light .brand-mark__cells { fill:#efede6; }
.tone-dark .brand-mark__stem,.tone-dark .brand-mark__cells { fill:#11110f; }
</style>
