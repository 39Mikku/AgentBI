<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView v-slot="{ Component }">
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
</style>
