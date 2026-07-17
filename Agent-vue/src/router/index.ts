import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/assistants',
      name: 'assistants',
      component: () => import('@/views/AssistantsView.vue'),
      meta: { title: '助手管理 · AgentBI', requiresAuth: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/LandingView.vue'),
      meta: { title: 'AgentBI · 智能体工作台' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '登录 · AgentBI' },
    },
    {
      path: '/home',
      name: 'authenticated-home',
      component: () => import('@/views/AuthenticatedHomeView.vue'),
      meta: { title: '今日主页 · AgentBI', requiresAuth: true },
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { title: 'Obsidian · AgentBI', requiresAuth: true },
    },
    {
      path: '/attachments',
      name: 'attachments',
      component: () => import('@/views/AttachmentsView.vue'),
      meta: { title: '附件库 · AgentBI', requiresAuth: true },
    },
    {
      path: '/live',
      name: 'live',
      component: () => import('@/views/LiveView.vue'),
      meta: { title: 'Live · AgentBI', requiresAuth: true },
    },
    {
      path: '/test',
      name: 'test',
      component: () => import('@/views/TestView.vue'),
      meta: { title: 'Test Lab · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox',
      name: 'toolbox',
      component: () => import('@/views/ToolboxView.vue'),
      meta: { title: '工具箱 · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox/voice',
      name: 'voice-workbench',
      component: () => import('@/views/VoiceWorkbenchView.vue'),
      meta: { title: 'Voice Lab · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox/file-time',
      name: 'file-time-workbench',
      component: () => import('@/views/FileTimeView.vue'),
      meta: { title: 'File Time · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox/auto-input',
      name: 'auto-input-workbench',
      component: () => import('@/views/AutoInputView.vue'),
      meta: { title: 'Auto Type · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox/moegirl',
      name: 'moegirl-archive',
      component: () => import('@/views/MoegirlArchiveView.vue'),
      meta: { title: 'Moe Archive · AgentBI', requiresAuth: true },
    },
    {
      path: '/toolbox/emoji',
      name: 'emoji-sticker-workbench',
      component: () => import('@/views/EmojiStickerView.vue'),
      meta: { title: 'Emoji Press · AgentBI', requiresAuth: true },
    },
    {
      path: '/settings/models',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { title: '模型工作室 · AgentBI', requiresAuth: true },
    },
    {
      path: '/settings/capabilities',
      name: 'capability-settings',
      component: () => import('@/views/SubagentSettingsView.vue'),
      meta: { title: '能力配置 · AgentBI', requiresAuth: true },
    },
    { path: '/settings/subagents', redirect: '/settings/capabilities' },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
      meta: { title: '关于 · AgentBI' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: '页面未找到 · AgentBI' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated)
    return { name: 'login', query: { redirect: to.fullPath } }
  if ((to.name === 'home' || to.name === 'login') && auth.isAuthenticated)
    return { name: 'authenticated-home' }
  return true
})
router.afterEach((to) => {
  if (to.meta.title) document.title = String(to.meta.title)
})
export default router
