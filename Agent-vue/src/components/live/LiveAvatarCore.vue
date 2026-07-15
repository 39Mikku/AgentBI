<script setup lang="ts">
import { hasRoleAvatar } from '@/live/role-presentation'

defineProps<{
  name: string
  avatar?: string | null
  phase: string
  muted: boolean
}>()
</script>

<template>
  <div class="orbital-field" :class="[`phase-${phase}`, { muted }]">
    <div class="orbit orbit-a"><i></i></div>
    <div class="orbit orbit-b"><i></i></div>
    <div class="orbit orbit-c"></div>
    <div class="signal-halo"></div>
    <div class="role-core">
      <img v-if="hasRoleAvatar(avatar)" :src="avatar || undefined" :alt="name" />
      <div class="core-shade"></div>
    </div>
    <div class="wave-ring" aria-hidden="true">
      <i v-for="index in 24" :key="index"></i>
    </div>
  </div>
</template>

<style scoped>
.orbital-field { width: clamp(290px, 31vw, 430px); aspect-ratio: 1; display: grid; place-items: center; position: relative; }
.orbit { position: absolute; border-radius: 50%; border: 1px solid rgba(159,255,216,.15); }
.orbit-a { inset: 0; border-style: dashed; animation: rotate 34s linear infinite; }
.orbit-b { inset: 11%; border-color: rgba(159,255,216,.24); animation: rotate 22s linear infinite reverse; }
.orbit-c { inset: 25%; border-color: rgba(159,255,216,.16); }
.orbit i { position: absolute; width: 7px; height: 7px; border-radius: 50%; top: -4px; left: calc(50% - 3px); background: #9fffd8; box-shadow: 0 0 18px #9fffd8; }
.signal-halo { position: absolute; inset: 20%; border-radius: 50%; background: radial-gradient(circle, rgba(74,204,153,.15), transparent 68%); filter: blur(3px); transition: transform .35s ease; }
.role-core { width: 42%; aspect-ratio: 1; border-radius: 50%; overflow: hidden; position: relative; display: grid; place-items: center; background: #14251f; border: 1px solid rgba(159,255,216,.5); box-shadow: 0 0 0 13px rgba(159,255,216,.025), 0 0 70px rgba(54,202,148,.2); z-index: 2; }
.role-core img { width: 100%; height: 100%; object-fit: cover; }
.core-shade { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(145deg, rgba(255,255,255,.11), transparent 38%, rgba(0,0,0,.3)); }
.wave-ring { position: absolute; inset: 23%; display: flex; align-items: center; justify-content: center; gap: 3px; z-index: 3; pointer-events: none; }
.wave-ring i { width: 2px; height: 5px; background: #9fffd8; opacity: .72; transform-origin: center; animation: signal 1.2s ease-in-out infinite alternate; }
.wave-ring i:nth-child(3n) { animation-delay: -.34s; }.wave-ring i:nth-child(4n) { animation-delay: -.62s; }.wave-ring i:nth-child(5n) { animation-delay: -.9s; }
.phase-speaking .wave-ring i, .phase-listening .wave-ring i { animation-duration: .4s; }.phase-speaking .signal-halo { transform: scale(1.12); }
.muted { filter: saturate(.3); }.muted .wave-ring i { animation-play-state: paused; }
@keyframes rotate { to { transform: rotate(360deg); } }
@keyframes signal { to { height: 40px; opacity: 1; } }
@media (max-width: 760px) { .orbital-field { width: min(75vw, 330px); } }
</style>
