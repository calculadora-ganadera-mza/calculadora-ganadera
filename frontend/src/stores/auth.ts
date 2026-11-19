import { computed, shallowRef, watch } from 'vue'
import { defineStore } from 'pinia'

export type Role = 'producer' | 'technician' | 'admin'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = shallowRef<string | null>(null)
  const authenticationRequired = shallowRef(false)
  const isAuthenticated = computed(() => accessToken.value !== null)
  // Rol del usuario de la sesión, leído de /auth/me; null hasta que se lee
  const role = shallowRef<Role | null>(null)
  const isAdmin = computed(() => role.value === 'admin')

  // Al cerrar o perder la sesión, el rol deja de valer
  watch(accessToken, (token) => {
    if (token === null) role.value = null
  })

  return { accessToken, authenticationRequired, isAuthenticated, role, isAdmin }
})
