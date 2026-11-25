import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { useAuthStore } from '../stores/auth'
import { loadRole } from '../api/users'

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
    path: '/farm/scenarios',
    name: 'scenarios',
    component: () => import('../views/FarmView.vue'),
    meta: { title: 'Mi campo' },
  },
  {
    path: '/farm/:scenarioId',
    name: 'scenario',
    component: () => import('../views/ScenarioView.vue'),
    meta: { title: 'Escenario' },
  },
  {
    path: '/farm/:scenarioId/sectors/new',
    name: 'new-sector',
    component: () => import('../views/NewSectorView.vue'),
    meta: { title: 'Dibujar sector' },
  },
  {
    path: '/farm/:scenarioId/sectors/:unitId',
    name: 'sector',
    component: () => import('../views/SectorView.vue'),
    meta: { title: 'Sector' },
  },
  {
    path: '/farm/:scenarioId/sectors/:unitId/water-points/new',
    name: 'new-water-point',
    component: () => import('../views/WaterPointView.vue'),
    meta: { title: 'Ubicar aguada' },
  },
  {
    path: '/farm/:scenarioId/sectors/:unitId/water-points/:waterPointId',
    name: 'water-point',
    component: () => import('../views/WaterPointView.vue'),
    meta: { title: 'Editar aguada' },
  },
  {
    path: '/calculators',
    name: 'calculators',
    component: () => import('../views/CalculatorsView.vue'),
    meta: { title: 'Calculadoras' },
  },
  {
    path: '/calculators/carrying-capacity',
    name: 'carrying-capacity',
    component: () => import('../views/CarryingCapacityView.vue'),
    meta: { title: 'Calcular receptividad' },
  },
  {
    path: '/calculators/carrying-capacity/:scenarioId/:unitId/:seasonId',
    name: 'carrying-capacity-result',
    component: () => import('../views/CarryingCapacityResultView.vue'),
    meta: { title: 'Receptividad' },
  },
  {
    path: '/tracking',
    name: 'tracking',
    component: () => import('../views/TrackingView.vue'),
    meta: { title: 'Seguimiento' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/AdminView.vue'),
    meta: { title: 'Administración', adminOnly: true },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isAuthenticated && to.name !== 'login') return { name: 'login', replace: true }
  if (auth.isAuthenticated && to.name === 'login') return { name: 'home', replace: true }
  if (auth.isAuthenticated && auth.role === null) await loadRole()
  if (to.meta.adminOnly && !auth.isAdmin) return { name: 'home', replace: true }
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · Calculadora ganadera`
    : 'Calculadora ganadera'
})

export default router
