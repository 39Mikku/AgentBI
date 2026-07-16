<script setup lang="ts">
defineProps<{
  index: string
  title: string
  description: string
  to: string
  accent: string
  variant: 'hero' | 'signal' | 'paper' | 'utility'
}>()
</script>

<template>
  <RouterLink
    class="module-entry"
    :class="`module-entry--${variant}`"
    :to="to"
    :style="{ '--entry-accent': accent }"
  >
    <span class="entry-index">{{ index }} / {{ variant }}</span>
    <div class="entry-art" aria-hidden="true">
      <template v-if="variant === 'hero'">
        <span class="orbit orbit-a"></span>
        <span class="orbit orbit-b"></span>
        <span class="orbit-dot"></span>
      </template>
      <template v-else-if="variant === 'signal'">
        <i v-for="height in [18, 42, 28, 69, 36, 84, 47, 62, 25]" :key="height" :style="{ height: `${height}%` }"></i>
      </template>
      <template v-else-if="variant === 'paper'">
        <span v-for="n in 4" :key="n">0{{ n }}</span>
      </template>
      <template v-else>
        <i></i><i></i><i></i><i></i>
      </template>
    </div>
    <div class="entry-copy">
      <p>{{ description }}</p>
      <h2>{{ title }}</h2>
    </div>
    <span class="entry-action">进入模块 <b>↗</b></span>
  </RouterLink>
</template>

<style scoped>
.module-entry {
  --entry-accent: #d9ff36;
  position: relative;
  min-height: 265px;
  overflow: hidden;
  border: 1px solid rgba(239, 237, 230, 0.14);
  background: #171714;
  color: #efede6;
  padding: 22px;
  isolation: isolate;
  transition: color .35s ease, background .35s ease, transform .35s cubic-bezier(.2,.75,.2,1);
}
.module-entry::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--entry-accent);
  transform: translateY(101%);
  transition: transform .45s cubic-bezier(.2,.8,.2,1);
}
.module-entry:hover,
.module-entry:focus-visible { color: #11110f; transform: translateY(-4px); }
.module-entry:hover::after,
.module-entry:focus-visible::after { transform: translateY(0); }
.module-entry:focus-visible { outline: 2px solid var(--entry-accent); outline-offset: 3px; }
.entry-index {
  position: relative;
  z-index: 2;
  font: 500 9px 'DM Mono', monospace;
  letter-spacing: .14em;
  text-transform: uppercase;
  opacity: .62;
}
.entry-art { position: absolute; inset: 48px 22px auto; height: 90px; }
.entry-copy { position: absolute; left: 22px; right: 22px; bottom: 48px; z-index: 2; }
.entry-copy p { max-width: 250px; margin-bottom: 6px; color: #77746d; font-size: 10px; transition: color .35s; }
.module-entry:hover .entry-copy p,
.module-entry:focus-visible .entry-copy p { color: rgba(17,17,15,.6); }
.entry-copy h2 { font: 700 clamp(34px, 4vw, 58px)/.88 Manrope, sans-serif; letter-spacing: -.07em; text-transform: uppercase; }
.entry-action { position: absolute; right: 20px; bottom: 18px; z-index: 2; font: 500 9px 'DM Mono', monospace; letter-spacing: .08em; }
.entry-action b { display: inline-block; margin-left: 5px; transition: transform .3s; }
.module-entry:hover .entry-action b { transform: translate(3px,-3px); }

.module-entry--hero { grid-column: span 2; min-height: 360px; }
.module-entry--hero .entry-copy h2 { font-size: clamp(56px, 7vw, 98px); }
.module-entry--hero .entry-art { inset: 28px 25px auto auto; width: 48%; height: 75%; }
.orbit { position: absolute; border: 1px solid rgba(217,255,54,.45); border-radius: 50%; transition: border-color .35s, transform .7s; }
.orbit-a { width: 180px; height: 180px; right: 1%; top: 5%; }
.orbit-b { width: 112px; height: 112px; right: 83px; top: 40px; border-style: dashed; }
.orbit-dot { position: absolute; width: 15px; height: 15px; right: 42px; top: 52px; background: var(--entry-accent); border-radius: 50%; box-shadow: 0 0 0 10px rgba(217,255,54,.08); }
.module-entry--hero:hover .orbit-a { border-color: rgba(17,17,15,.5); transform: rotate(15deg) scale(1.08); }
.module-entry--hero:hover .orbit-b { border-color: rgba(17,17,15,.5); transform: rotate(-25deg); }

.module-entry--signal .entry-art { display: flex; align-items: center; gap: 6px; border-block: 1px solid rgba(239,237,230,.13); padding: 12px 0; }
.module-entry--signal .entry-art i { flex: 1; background: var(--entry-accent); transition: height .45s, background .35s; }
.module-entry--signal:hover .entry-art { border-color: rgba(17,17,15,.2); }
.module-entry--signal:hover .entry-art i { background: #11110f; }
.module-entry--signal:hover .entry-art i:nth-child(2n) { height: 92% !important; }

.module-entry--paper { background: #e4e0d5; color: #11110f; }
.module-entry--paper::after { background: var(--entry-accent); }
.module-entry--paper .entry-copy p { color: #6d6a62; }
.module-entry--paper .entry-art { display: grid; grid-template-columns: repeat(4,1fr); gap: 1px; border: 1px solid rgba(17,17,15,.25); }
.module-entry--paper .entry-art span { display: grid; place-items: center; border-right: 1px solid rgba(17,17,15,.18); font: 10px 'DM Mono', monospace; }
.module-entry--paper .entry-art span:last-child { border: 0; }
.module-entry--paper:hover .entry-art span:nth-child(3) { background: #11110f; color: var(--entry-accent); }

.module-entry--utility { grid-column: span 2; }
.module-entry--utility .entry-art { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; }
.module-entry--utility .entry-art i { border: 1px solid #595850; position: relative; }
.module-entry--utility .entry-art i::after { content: ''; position: absolute; width: 7px; height: 7px; right: 6px; bottom: 6px; background: var(--entry-accent); }
.module-entry--utility:hover .entry-art i { border-color: rgba(17,17,15,.45); }
.module-entry--utility:hover .entry-art i::after { background: #11110f; }

@media (max-width: 820px) {
  .module-entry--hero, .module-entry--utility { grid-column: auto; }
  .module-entry--hero .entry-copy h2 { font-size: clamp(50px, 15vw, 78px); }
}
@media (prefers-reduced-motion: reduce) {
  .module-entry, .module-entry::after, .module-entry * { transition: none !important; }
}
</style>
