<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'

import BrandRouteLoader from '@/components/brand/BrandRouteLoader.vue'
import router from '@/router'
import WorkspaceSetup from '@/components/WorkspaceSetup.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
onMounted(() => workspace.initialize())

const routeBusy = ref(true)
let settleTimer: ReturnType<typeof setTimeout> | undefined

function settleRoute(delay = 320) {
  if (settleTimer) clearTimeout(settleTimer)
  settleTimer = setTimeout(() => { routeBusy.value = false }, delay)
}

const removeBeforeHook = router.beforeEach(() => {
  if (settleTimer) clearTimeout(settleTimer)
  routeBusy.value = true
  return true
})
const removeAfterHook = router.afterEach(() => settleRoute())

onMounted(() => settleRoute(520))
onBeforeUnmount(() => {
  if (settleTimer) clearTimeout(settleTimer)
  removeBeforeHook()
  removeAfterHook()
})
</script>

<template>
  <Transition name="brand-loader-fade">
    <BrandRouteLoader v-if="routeBusy" />
  </Transition>
  <WorkspaceSetup v-if="!workspace.ready" />
  <RouterView v-else v-slot="{ Component }">
    <Transition name="route" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>

<style>
.route-enter-active,
.route-leave-active {
  transition: opacity 0.28s ease;
}
.route-enter-from,
.route-leave-to {
  opacity: 0;
}
.brand-loader-fade-enter-active,
.brand-loader-fade-leave-active {
  transition: opacity 0.24s ease;
}
.brand-loader-fade-enter-from,
.brand-loader-fade-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .route-enter-active,
  .route-leave-active,
  .brand-loader-fade-enter-active,
  .brand-loader-fade-leave-active {
    transition: none;
  }
}
</style>
