import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/assistants',
      name: 'assistants',
      component: () => import('@/views/AssistantsView.vue'),
      meta: { title: '助手管理 · AgentBI' },
    },
    {
      path: '/',
      alias: '/home',
      name: 'home',
      component: () => import('@/views/WorkspaceHomeView.vue'),
      meta: { title: '今日主页 · AgentBI' },
    },
    { path: '/login', redirect: '/' },
    { path: '/about', redirect: '/' },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { title: 'Obsidian · AgentBI' },
    },
    {
      path: '/attachments',
      name: 'attachments',
      component: () => import('@/views/AttachmentsView.vue'),
      meta: { title: '附件库 · AgentBI' },
    },
    {
      path: '/live',
      name: 'live',
      component: () => import('@/views/LiveView.vue'),
      meta: { title: 'Live · AgentBI' },
    },
    {
      path: '/playground/manage',
      name: 'playground-manage',
      component: () => import('@/views/PlaygroundProfilesView.vue'),
      meta: { title: '角色与世界 · AgentBI' },
    },
    {
      path: '/playground',
      name: 'playground',
      component: () => import('@/views/PlaygroundView.vue'),
      meta: { title: 'Playground · AgentBI' },
    },
    {
      path: '/test',
      name: 'test',
      component: () => import('@/views/TestView.vue'),
      meta: { title: 'Test Lab · AgentBI' },
    },
    {
      path: '/toolbox',
      name: 'toolbox',
      component: () => import('@/views/ToolboxView.vue'),
      meta: { title: '工具箱 · AgentBI' },
    },
    {
      path: '/toolbox/voice',
      name: 'voice-workbench',
      component: () => import('@/views/VoiceWorkbenchView.vue'),
      meta: { title: 'Voice Lab · AgentBI' },
    },
    {
      path: '/toolbox/file-time',
      name: 'file-time-workbench',
      component: () => import('@/views/FileTimeView.vue'),
      meta: { title: 'File Time · AgentBI' },
    },
    {
      path: '/toolbox/auto-input',
      name: 'auto-input-workbench',
      component: () => import('@/views/AutoInputView.vue'),
      meta: { title: 'Auto Type · AgentBI' },
    },
    {
      path: '/toolbox/moegirl',
      name: 'moegirl-archive',
      component: () => import('@/views/MoegirlArchiveView.vue'),
      meta: { title: 'Moe Archive · AgentBI' },
    },
    {
      path: '/toolbox/emoji',
      name: 'emoji-sticker-workbench',
      component: () => import('@/views/EmojiStickerView.vue'),
      meta: { title: 'Emoji Press · AgentBI' },
    },
    {
      path: '/settings/models',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { title: '模型工作室 · AgentBI' },
    },
    {
      path: '/settings/capabilities',
      name: 'capability-settings',
      component: () => import('@/views/SubagentSettingsView.vue'),
      meta: { title: '能力配置 · AgentBI' },
    },
    { path: '/settings/subagents', redirect: '/settings/capabilities' },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: '页面未找到 · AgentBI' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  if (to.meta.title) document.title = String(to.meta.title)
})
export default router
