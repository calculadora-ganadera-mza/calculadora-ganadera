import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = shallowRef<string | null>(null)
  const authenticationRequired = shallowRef(false)
  const isAuthenticated = computed(() => accessToken.value !== null)

  return { accessToken, authenticationRequired, isAuthenticated }
})
