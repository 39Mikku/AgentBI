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
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { title: 'Obsidian · AgentBI', requiresAuth: true },
    },
    {
      path: '/settings/models',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { title: '模型工作室 · AgentBI', requiresAuth: true },
    },
    {
      path: '/console',
      name: 'console',
      component: () => import('@/views/AboutView.vue'),
      meta: { title: '控制台 · AgentBI', requiresAuth: true },
    },
    { path: '/about', redirect: '/chat' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated)
    return { name: 'login', query: { redirect: to.fullPath } }
  if ((to.name === 'home' || to.name === 'login') && auth.isAuthenticated) return { name: 'chat' }
  return true
})
router.afterEach((to) => {
  if (to.meta.title) document.title = String(to.meta.title)
})
export default router
