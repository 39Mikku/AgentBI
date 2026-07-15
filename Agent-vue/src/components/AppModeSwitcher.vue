<script setup lang="ts">
defineProps<{ active: 'studio' | 'live' }>()
</script>

<template>
  <nav class="mode-switcher" aria-label="工作模式">
    <RouterLink to="/chat" :class="{ active: active === 'studio' }">
      <span class="mode-index">01</span><strong>Studio</strong><i></i>
    </RouterLink>
    <RouterLink to="/live" :class="{ active: active === 'live' }">
      <span class="mode-index">02</span><strong>Live</strong><i></i>
    </RouterLink>
  </nav>
</template>

<style scoped>
.mode-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  column-gap: 7px;
  padding: 8px 9px 7px;
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
  font: 8px/1 'DM Mono', monospace;
  letter-spacing: 0.08em;
  opacity: 0.58;
}
.mode-switcher strong {
  font: 600 10px/1.2 Manrope, sans-serif;
  letter-spacing: 0.08em;
  text-transform: uppercase;
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
</style>
