import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: '登录 · AgentBI' },
    },
    {
      path: '/console',
      name: 'console',
      component: () => import('@/views/AboutView.vue'),
      meta: { title: '控制台 · AgentBI', requiresAuth: true },
    },
    {
      path: '/about',
      redirect: '/console',
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'home', query: { redirect: to.fullPath } }
  }
  if (to.name === 'home' && auth.isAuthenticated) {
    return { name: 'console' }
  }
  return true
})

router.afterEach((to) => {
  if (to.meta.title) {
    document.title = String(to.meta.title)
  }
})

export default router
