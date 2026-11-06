import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { isAuthenticated } from '../api/auth'

// Secciones de la app. El título se muestra en la pestaña del navegador.
export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Iniciar sesión' },
  },
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { title: 'Inicio' },
  },
  {
    path: '/farm',
    name: 'farm',
    component: () => import('../views/FarmView.vue'),
    meta: { title: 'Mi campo' },
  },
  {
    path: '/calculators',
    name: 'calculators',
    component: () => import('../views/CalculatorsView.vue'),
    meta: { title: 'Calculadoras' },
  },
  {
    path: '/tracking',
    name: 'tracking',
    component: () => import('../views/TrackingView.vue'),
    meta: { title: 'Seguimiento' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: 'Página no encontrada' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  if (!isAuthenticated.value && to.name !== 'login') return { name: 'login', replace: true }
  if (isAuthenticated.value && to.name === 'login') return { name: 'home', replace: true }
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · Calculadora ganadera`
    : 'Calculadora ganadera'
})

export default router
