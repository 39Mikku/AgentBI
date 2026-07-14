<script setup lang="ts">
import { onMounted, ref } from 'vue'

type Theme = 'light' | 'dark'
const theme = ref<Theme>('light')
const STORAGE_KEY = 'agentbi_theme'

function apply(t: Theme) {
  theme.value = t
  document.documentElement.classList.toggle('dark', t === 'dark')
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, t)
  }
}

function toggle() {
  apply(theme.value === 'dark' ? 'light' : 'dark')
}

onMounted(() => {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
  if (saved === 'light' || saved === 'dark') {
    apply(saved)
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    apply(prefersDark ? 'dark' : 'light')
  }
})
</script>

<template>
  <button class="theme-toggle" type="button" :aria-label="theme === 'dark' ? '切换到浅色' : '切换到深色'" @click="toggle">
    <span class="icon-wrap" :class="{ 'is-dark': theme === 'dark' }">
      <!-- sun -->
      <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" />
      </svg>
      <!-- moon -->
      <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
      </svg>
    </span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--card);
  color: var(--foreground);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: border-color 0.2s ease, transform 0.2s ease, background-color 0.2s ease;
}
.theme-toggle:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
}
.theme-toggle:active {
  transform: translateY(0);
}

.icon-wrap {
  position: relative;
  width: 20px;
  height: 20px;
}
.icon-wrap svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transition: opacity 0.3s ease, transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.sun {
  opacity: 1;
  transform: rotate(0deg);
}
.moon {
  opacity: 0;
  transform: rotate(-90deg);
}
.icon-wrap.is-dark .sun {
  opacity: 0;
  transform: rotate(90deg);
}
.icon-wrap.is-dark .moon {
  opacity: 1;
  transform: rotate(0deg);
}
</style>
