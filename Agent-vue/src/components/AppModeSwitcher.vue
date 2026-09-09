<script setup lang="ts">
withDefaults(defineProps<{ active: 'studio' | 'live' | 'test' | 'playground'; collapsed?: boolean }>(), {
  collapsed: false,
})
</script>

<template>
  <nav class="mode-switcher" :class="{ collapsed }" aria-label="工作模式">
    <RouterLink to="/chat" title="Studio" :class="{ active: active === 'studio' }">
      <span class="mode-index">01</span><strong>Studio</strong><i></i>
    </RouterLink>
    <RouterLink to="/live" title="Live" :class="{ active: active === 'live' }">
      <span class="mode-index">02</span><strong>Live</strong><i></i>
    </RouterLink>
    <RouterLink to="/test" title="Test" :class="{ active: active === 'test' }">
      <span class="mode-index">03</span><strong>Test</strong><i></i>
    </RouterLink>
    <RouterLink to="/playground" title="Playground" :class="{ active: active === 'playground' }">
      <span class="mode-index">04</span><strong>Playground</strong><i></i>
    </RouterLink>
  </nav>
</template>

<style scoped>
.mode-switcher {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.035);
  padding: 3px;
  gap: 3px;
}
.mode-switcher a {
  min-width: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 5px;
  padding: 9px 5px 8px;
  color: rgba(255, 255, 255, 0.38);
  text-decoration: none;
  position: relative;
  overflow: hidden;
  transition: color 180ms ease, background 180ms ease;
}
.mode-switcher a:hover {
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.045);
}
.mode-switcher a.active {
  color: #f4f5ef;
  background: rgba(255, 255, 255, 0.09);
}
.mode-index {
  grid-row: 1 / 3;
  font: var(--control-font-size)/1 'DM Mono', monospace;
  letter-spacing: 0;
  opacity: 0.58;
}
.mode-switcher strong {
  font: 600 var(--control-font-size)/1.2 Manrope, sans-serif;
  letter-spacing: 0;
}
.mode-switcher i {
  width: 100%;
  height: 1px;
  margin-top: 5px;
  background: currentColor;
  transform: scaleX(0.18);
  transform-origin: left;
  opacity: 0.38;
  transition: transform 220ms ease, opacity 220ms ease;
}
.mode-switcher a.active i {
  transform: scaleX(1);
  opacity: 0.9;
}
.mode-switcher.collapsed {
  grid-template-columns: 1fr;
  gap: 4px;
}
.mode-switcher.collapsed a {
  display: grid;
  grid-template: 1fr / 1fr;
  place-items: center;
  min-height: 38px;
  padding: 0;
}
.mode-switcher.collapsed .mode-index {
  grid-row: auto;
  font-size: var(--control-font-size);
  opacity: 0.82;
}
.mode-switcher.collapsed strong,
.mode-switcher.collapsed i {
  display: none;
}
</style>
