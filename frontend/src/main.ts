import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { restoreSession } from './api/auth'

const app = createApp(App)

app.use(createPinia())

window.addEventListener('auth:required', () => {
  void router.replace('/login')
})

// Restore the in-memory access token before protected views mount.
async function start() {
  await restoreSession()
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void start()
