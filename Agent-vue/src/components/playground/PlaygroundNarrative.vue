<script setup lang="ts">
import type {
  PlaygroundMessage,
  PlaygroundProfile,
  PlaygroundSummary,
} from '@/api/playground-types'
import type { PlaygroundTtsStatus } from '@/playground/tts-player'
import PlaygroundActionOptions from './PlaygroundActionOptions.vue'
import PlaygroundMessageView from './PlaygroundMessage.vue'
import PlaygroundSummaryMarker from './PlaygroundSummaryMarker.vue'


const props = defineProps<{
  messages: PlaygroundMessage[]
  profile: PlaygroundProfile
  summary: PlaygroundSummary | null
  generating?: boolean
  ttsStates?: Record<string, { status: PlaygroundTtsStatus; error?: string }>
}>()
const emit = defineEmits<{
  retry: [messageId: string]
  edit: [message: PlaygroundMessage]
  branch: [messageId: string]
  version: [messageId: string]
  play: [message: PlaygroundMessage]
  option: [text: string]
  'summary-view': []
  'summary-edit': []
  'summary-refresh': []
}>()
function terminalOptions(message: PlaygroundMessage, index: number) {
  return message.role === 'assistant' && index === props.messages.length - 1 &&
    message.status === 'complete' && message.metadata.action_options?.length === 4
}
</script>

<template>
  <div class="narrative-column">
    <template v-for="(message, index) in messages" :key="message.id">
      <PlaygroundMessageView :message="message" :index="index" :opening="index === 0 && message.role === 'assistant'" :character-mode="profile.profile_type === 'character'" :tts-enabled="profile.settings.tts.enabled" :tts-status="ttsStates?.[message.id]?.status" :tts-error="ttsStates?.[message.id]?.error" @retry="emit('retry', $event)" @edit="emit('edit', $event)" @branch="emit('branch', $event)" @version="emit('version', $event)" @play="emit('play', $event)" />
      <PlaygroundActionOptions v-if="terminalOptions(message, index)" :options="message.metadata.action_options!" :disabled="generating" @select="emit('option', $event)" />
      <PlaygroundSummaryMarker v-if="summary?.summarized_through_message_id === message.id" :summary="summary" @view="emit('summary-view')" @edit="emit('summary-edit')" @refresh="emit('summary-refresh')" />
    </template>
  </div>
</template>

<style scoped>
.narrative-column{width:min(720px,calc(100vw - 80px));margin:0 auto;padding:72px 0 230px}@media(max-width:700px){.narrative-column{width:calc(100vw - 34px);padding-top:48px}}
</style>
