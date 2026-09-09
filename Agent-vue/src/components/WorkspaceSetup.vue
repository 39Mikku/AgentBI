<script setup lang="ts">
import BrandMark from '@/components/brand/BrandMark.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
</script>

<template>
  <main class="workspace-setup">
    <section aria-labelledby="setup-title">
      <BrandMark />
      <p class="eyebrow">AGENTBI · LOCAL WORKSPACE</p>
      <h1 id="setup-title">{{ workspace.loading ? '正在打开工作台' : workspace.error ? '连接工作台' : '继续你的工作' }}</h1>
      <p v-if="workspace.error" role="alert">{{ workspace.error }}</p>
      <p v-else-if="workspace.loading" role="status">正在读取本地资料…</p>
      <p v-else>发现多份历史资料，选择本次使用的工作区。聊天、助手与记忆会沿用原来的记录。</p>
      <div v-if="!workspace.loading" class="profiles">
        <button v-for="item in workspace.profiles" :key="item.user_id" @click="workspace.initialize(item.user_id)">
          <strong>{{ item.username }}</strong><span>{{ item.email || item.user_id }}</span>
        </button>
        <button v-if="workspace.error" @click="workspace.initialize()">重新连接</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.workspace-setup { min-height: 100dvh; display: grid; place-items: center; background: #eeece5; color: #171717; padding: 24px; }
section { width: min(100%, 480px); }
.brand-mark { width: 64px; height: 64px; }
.eyebrow { margin-top: 28px; font-size: 11px; letter-spacing: .15em; }
h1 { font-size: clamp(28px, 5vw, 40px); margin: 16px 0; }
p { line-height: 1.8; }
.profiles { display: grid; gap: 10px; margin-top: 28px; }
button { text-align: left; padding: 18px; background: #fffdf7; color: inherit; border: 1px solid #bdb9ad; cursor: pointer; display: grid; gap: 6px; }
button:hover, button:focus-visible { background: #d9ff36; outline: 2px solid #171717; outline-offset: 2px; }
button span { font-size: var(--control-font-size); overflow-wrap: anywhere; }
</style>
