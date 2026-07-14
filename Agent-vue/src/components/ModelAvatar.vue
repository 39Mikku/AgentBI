<script setup lang="ts">
import { computed } from 'vue'
import { resolveModelBrand } from '@/utils/model-avatar'

const props = withDefaults(defineProps<{ model?: string | null; size?: 'small' | 'regular'; variant?: 'pixel' | 'bare' }>(), { size: 'regular', variant: 'pixel' })
const brand = computed(() => resolveModelBrand(props.model))
</script>

<template>
  <span class="model-avatar" :class="[size, variant]" :title="brand.name" :style="{ '--brand': brand.accent }">
    <svg v-if="brand.icon" viewBox="0 0 24 24" aria-hidden="true"><path :d="brand.icon.path" /></svg>
    <span v-else>{{ brand.fallback }}</span>
  </span>
</template>

<style scoped>
.model-avatar{--brand:#111;display:grid;place-items:center;width:32px;height:32px;flex:none;background:#f8f7f2;color:var(--brand);border:2px solid currentColor;box-shadow:3px 3px 0 color-mix(in srgb,var(--brand) 22%,transparent);clip-path:polygon(0 5px,5px 5px,5px 0,100% 0,100% calc(100% - 5px),calc(100% - 5px) calc(100% - 5px),calc(100% - 5px) 100%,0 100%)}.model-avatar.small{width:24px;height:24px;border-width:1.5px;box-shadow:2px 2px 0 color-mix(in srgb,var(--brand) 22%,transparent);clip-path:none}.model-avatar svg{width:61%;height:61%;fill:currentColor}.model-avatar span{font:800 8px/1 'DM Mono',monospace;letter-spacing:-.13em}.model-avatar.small span{font-size:7px}
.model-avatar.bare{border:0;background:transparent;box-shadow:none;clip-path:none}
</style>
