import { computed, shallowRef, watch } from 'vue'
import { defineStore } from 'pinia'
import type { CurrentUser } from '../api/users'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = shallowRef<string | null>(null)
  const authenticationRequired = shallowRef(false)
  const isAuthenticated = computed(() => accessToken.value !== null)
  // Usuario de la sesión, leído de /auth/me; null hasta que se lee
  const user = shallowRef<CurrentUser | null>(null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // Al cerrar o perder la sesión, los datos del usuario dejan de valer
  watch(accessToken, (token) => {
    if (token === null) user.value = null
  })

  return { accessToken, authenticationRequired, isAuthenticated, user, isAdmin }
})
