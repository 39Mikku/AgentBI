<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { PROJECT_AUTHOR, PROJECT_LINKS } from '@/project/project-surfaces'
import { useAuthStore } from '@/stores/auth'

withDefaults(defineProps<{
  compact?: boolean
  tone?: 'paper' | 'dark'
}>(), {
  compact: false,
  tone: 'paper',
})

const auth = useAuthStore()
const workspaceLink = computed(() => auth.isAuthenticated ? '/home' : '/login')
const workspaceLabel = computed(() => auth.isAuthenticated ? '返回工作空间' : '进入工作台')
</script>

<template>
  <footer class="project-footer" :class="[tone, { compact }]">
    <div class="project-footer__identity">
      <span>AGENTBI / PERSONAL INTELLIGENCE SYSTEM</span>
      <p>BUILT BY <strong>{{ PROJECT_AUTHOR }}</strong> · EXPANDED BY CURIOSITY</p>
    </div>

    <nav aria-label="项目信息">
      <template v-for="link in PROJECT_LINKS" :key="link.label">
        <a
          v-if="link.external"
          :href="link.href"
          target="_blank"
          rel="noreferrer"
        >{{ link.label }} <b>↗</b></a>
        <RouterLink v-else :to="link.href">{{ link.label }}</RouterLink>
      </template>
    </nav>

    <RouterLink v-if="compact" class="compact-about" to="/about">About</RouterLink>

    <div class="project-footer__status">
      <span><i></i> LOCAL FIRST · BUILD IN PROGRESS</span>
      <RouterLink :to="workspaceLink">{{ workspaceLabel }} <b>↗</b></RouterLink>
    </div>
  </footer>
</template>

<style scoped>
.project-footer {
  --footer-ink: #11110f;
  --footer-muted: #77736b;
  --footer-line: #bbb6aa;
  --footer-acid: #ccff24;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto minmax(220px, 1fr);
  align-items: center;
  gap: 28px;
  min-height: 112px;
  border-top: 1px solid var(--footer-line);
  color: var(--footer-muted);
  font: 8px 'DM Mono', var(--font-mono), monospace;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.project-footer.dark {
  --footer-ink: #f1efe8;
  --footer-muted: rgb(241 239 232 / 0.48);
  --footer-line: rgb(241 239 232 / 0.16);
}

.project-footer__identity,
.project-footer__status {
  display: grid;
  gap: 9px;
}

.project-footer__identity p {
  margin: 0;
  color: var(--footer-ink);
  font-size: 9px;
}

.project-footer__identity strong {
  font-weight: 700;
}

nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
}

a {
  position: relative;
  color: var(--footer-ink);
  text-decoration: none;
  white-space: nowrap;
}

a::after {
  position: absolute;
  right: 0;
  bottom: -5px;
  left: 0;
  height: 1px;
  background: currentColor;
  content: '';
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 180ms ease;
}

a:hover::after,
a:focus-visible::after {
  transform: scaleX(1);
  transform-origin: left;
}

a:focus-visible {
  outline: 2px solid var(--footer-acid);
  outline-offset: 6px;
}

a b {
  font-weight: 400;
}

.project-footer__status {
  justify-items: end;
  text-align: right;
}

.project-footer__status > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.project-footer__status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--footer-acid);
  box-shadow: 0 0 0 3px rgb(204 255 36 / 0.12);
}

.compact {
  min-height: 62px;
  grid-template-columns: minmax(0, 1fr) auto auto;
}

.compact nav,
.compact .project-footer__identity p {
  display: none;
}

.compact-about {
  display: inline-flex;
}

.compact .project-footer__status {
  display: flex;
  align-items: center;
  gap: 20px;
}

@media (max-width: 840px) {
  .project-footer {
    grid-template-columns: 1fr auto;
  }

  .project-footer.compact {
    grid-template-columns: minmax(0, 1fr) auto auto;
  }

  nav {
    grid-row: 2;
    justify-content: flex-start;
  }

  .project-footer__status {
    grid-column: 2;
    grid-row: 1 / span 2;
  }

  .compact nav {
    display: none;
  }
}

@media (max-width: 580px) {
  .project-footer,
  .project-footer.compact {
    grid-template-columns: 1fr;
    align-items: start;
    gap: 18px;
    padding-block: 25px;
  }

  .project-footer__status,
  .compact .project-footer__status {
    grid-column: 1;
    grid-row: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    justify-items: start;
    gap: 14px;
    text-align: left;
  }

  nav {
    grid-row: auto;
    flex-wrap: wrap;
    gap: 14px;
  }

  .compact-about {
    justify-self: start;
  }

  .project-footer__identity p {
    line-height: 1.6;
  }
}

@media (prefers-reduced-motion: reduce) {
  a::after {
    transition: none;
  }
}
</style>
