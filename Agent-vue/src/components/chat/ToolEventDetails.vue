<script setup lang="ts">
import { computed } from 'vue'
import {
  formatToolEventContent,
  toolEventSummary,
  type ToolEventType,
} from '@/utils/tool-event'

const props = defineProps<{ type: ToolEventType; tool?: string; content?: string }>()
const summary = computed(() => toolEventSummary(props.tool, props.type, props.content))
const detail = computed(() => formatToolEventContent(props.content))
</script>

<template>
  <div v-if="type === 'tool_started' || !detail" class="tool-event tool-event-running">
    <span class="tool-signal"></span>{{ summary }}
  </div>
  <details v-else class="tool-event tool-event-result">
    <summary>
      <span class="tool-signal"></span>
      <b>{{ summary }}</b>
      <i>查看详情</i>
    </summary>
    <pre>{{ detail }}</pre>
  </details>
</template>

<style scoped>
.tool-event {
  margin: 0 0 10px;
  border-left: 2px solid var(--acid);
  background: rgba(0, 0, 0, 0.035);
  color: #4b4b43;
  font: 11px/1.6 'DM Mono', monospace;
}
.tool-event-running {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
}
.tool-event summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  cursor: pointer;
  list-style: none;
}
.tool-event summary::-webkit-details-marker {
  display: none;
}
.tool-event summary b {
  font-weight: 500;
}
.tool-event summary i {
  margin-left: auto;
  color: #8a8880;
  font-size: 9px;
  font-style: normal;
}
.tool-event-result[open] summary i {
  font-size: 0;
}
.tool-event-result[open] summary i::before {
  content: '收起';
  font-size: 9px;
}
.tool-signal {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border: 1px solid #242421;
  background: var(--acid);
}
.tool-event pre {
  max-height: 320px;
  overflow: auto;
  margin: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding: 11px 13px 13px 25px;
  color: #5d5a54;
  font: 10px/1.65 'DM Mono', monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
