<script setup lang="ts">
import { computed, ref } from 'vue'

import type { PlaygroundMessage } from '@/api/playground-types'
import type { PlaygroundTtsStatus } from '@/playground/tts-player'
import { copyMarkdown } from '@/utils/clipboard'
import { renderMarkdown } from '@/utils/markdown'


const props = defineProps<{
  message: PlaygroundMessage
  index: number
  opening?: boolean
  characterMode?: boolean
  ttsEnabled?: boolean
  ttsStatus?: PlaygroundTtsStatus
  ttsError?: string
}>()
const emit = defineEmits<{
  retry: [messageId: string]
  edit: [message: PlaygroundMessage]
  branch: [messageId: string]
  version: [messageId: string]
  play: [message: PlaygroundMessage]
}>()
const copied = ref(false)
const html = computed(() => renderMarkdown(props.message.content))
const versions = computed(() => props.message.version_ids || [props.message.id])
const versionIndex = computed(() => props.message.sibling_index || 0)

async function copy() {
  await copyMarkdown(props.message.content)
  copied.value = true
  window.setTimeout(() => { copied.value = false }, 1200)
}

function move(offset: number) {
  const target = versions.value[versionIndex.value + offset]
  if (target) emit('version', target)
}
</script>

<template>
  <article class="story-message" :class="[message.role, message.status]">
    <header>
      <span class="message-index">{{ String(index + 1).padStart(3, '0') }}</span>
      <div><b>{{ message.role === 'assistant' ? (opening ? 'OPENING SCENE' : 'NARRATIVE') : 'YOUR ACTION' }}</b><time>{{ message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : message.status === 'streaming' ? 'NOW' : '' }}</time></div>
      <i></i>
    </header>
    <details v-if="message.reasoning_summary" class="reasoning"><summary>推理摘要</summary><p>{{ message.reasoning_summary }}</p></details>
    <div v-if="message.content" class="message-markdown" v-html="html"></div>
    <div v-else-if="message.status === 'streaming'" class="typing"><i></i><i></i><i></i><span>故事正在继续</span></div>
    <p v-if="message.status === 'error'" class="message-error">生成中断，可重试这一版本。</p>
    <footer v-if="message.status !== 'streaming'">
      <div class="message-actions">
        <button v-if="message.role === 'assistant' && !opening" @click="emit('retry', message.id)">重试</button>
        <button v-if="message.role === 'user' || opening" @click="emit('edit', message)">编辑</button>
        <button @click="emit('branch', message.id)">创建分支</button>
        <button @click="copy">{{ copied ? '已复制' : '复制 MD' }}</button>
        <button v-if="message.role === 'assistant' && characterMode && ttsEnabled && message.content" :disabled="ttsStatus === 'loading'" @click="emit('play', message)">{{ ttsStatus === 'loading' ? '生成语音…' : ttsStatus === 'playing' ? '播放中' : '朗读' }}</button>
      </div>
      <div v-if="(message.sibling_count || 1) > 1" class="versions"><button :disabled="versionIndex <= 0" @click="move(-1)">←</button><span>{{ versionIndex + 1 }} / {{ message.sibling_count }}</span><button :disabled="versionIndex >= (message.sibling_count || 1) - 1" @click="move(1)">→</button></div>
    </footer>
    <p v-if="ttsError" class="tts-error">{{ ttsError }}</p>
  </article>
</template>

<style scoped>
.story-message{position:relative;padding:24px 0 16px;color:#dfe4df}.story-message+ .story-message{border-top:1px solid rgba(255,255,255,.075)}.story-message>header{display:grid;grid-template-columns:31px auto 1fr;align-items:center;gap:10px;margin-bottom:17px}.message-index{color:#535c55;font:7px var(--font-mono)}.story-message>header div{display:flex;align-items:center;gap:9px}.story-message>header b{color:#7b847d;font:7px var(--font-mono);letter-spacing:.15em}.story-message.user>header b{color:var(--scene-acid)}.story-message>header time{color:#4e5750;font:6px var(--font-mono)}.story-message>header>i{height:1px;background:rgba(255,255,255,.09)}.message-markdown{font:400 15px/1.9 'Noto Serif SC','Source Han Serif SC','Songti SC',serif;letter-spacing:.015em;text-wrap:pretty}.user .message-markdown{color:#aeb6af;font-size:13px;font-style:italic}.message-markdown :deep(p){margin:0 0 1em}.message-markdown :deep(p:last-child){margin-bottom:0}.message-markdown :deep(h1),.message-markdown :deep(h2),.message-markdown :deep(h3){margin:1.5em 0 .6em;font-family:var(--font-display);line-height:1.2}.message-markdown :deep(blockquote){margin:1.1em 0;padding-left:16px;border-left:2px solid var(--scene-acid);color:#b6beb7}.message-markdown :deep(code){padding:2px 5px;background:rgba(255,255,255,.08);font:11px var(--font-mono)}.message-markdown :deep(pre){overflow:auto;padding:13px;background:#0b0e0c}.message-markdown :deep(img){max-width:100%;border:1px solid rgba(255,255,255,.13)}.reasoning{margin:0 0 17px;border-left:1px solid #485049;padding-left:11px;color:#747d76}.reasoning summary{font:7px var(--font-mono);cursor:pointer}.reasoning p{margin:8px 0 0;font:8px/1.65 var(--font-mono);white-space:pre-wrap}.story-message>footer{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-top:17px;opacity:0;transition:opacity .2s}.story-message:hover>footer,.story-message:focus-within>footer{opacity:1}.message-actions{display:flex;flex-wrap:wrap;gap:3px}.message-actions button,.versions button{border:0;background:rgba(255,255,255,.045);color:#687169;padding:6px 8px;font:6px var(--font-mono);cursor:pointer}.message-actions button:hover,.versions button:hover{color:var(--scene-acid)}.versions{display:flex;align-items:center;gap:4px}.versions span{color:#69726b;font:6px var(--font-mono)}.versions button:disabled{opacity:.25}.typing{display:flex;align-items:center;gap:5px;color:#687169;font:8px var(--font-mono)}.typing i{width:4px;height:4px;background:var(--scene-acid);animation:typing 1s ease-in-out infinite}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}.typing span{margin-left:7px}.message-error{color:#ff8a76;font:8px var(--font-mono)}@keyframes typing{50%{opacity:.2;transform:translateY(-3px)}}@media(max-width:700px){.story-message{padding-block:19px}.message-markdown{font-size:14px}.story-message>footer{opacity:1}.message-actions button{padding:6px}.story-message>header{grid-template-columns:25px auto 1fr}}
</style>
<style scoped>
.tts-error{margin:8px 0 0;color:#ff9a88;font:7px var(--font-mono)}
</style>
