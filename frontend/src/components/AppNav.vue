<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { logout } from '../api/auth'

const router = useRouter()
const accountMenu = ref<HTMLDetailsElement>()
const loggingOut = ref(false)
const logoutError = ref('')

function closeMenu() {
  if (accountMenu.value) accountMenu.value.open = false
}

function onFocusOut(event: FocusEvent) {
  if (!accountMenu.value?.contains(event.relatedTarget as Node | null)) closeMenu()
}

async function signOut() {
  loggingOut.value = true
  logoutError.value = ''
  try {
    await logout()
    closeMenu()
    await router.replace('/login')
  } catch {
    logoutError.value = 'No se pudo cerrar sesión. Intentá de nuevo.'
  } finally {
    loggingOut.value = false
  }
}

// Ícono de la app, servido desde public/
const appIcon = '/icon.svg'

// Secciones del menú. El ícono es el trazo de un SVG de 24x24.
const items = [
  {
    to: '/',
    label: 'Inicio',
    icon: 'M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  },
  {
    to: '/farm',
    label: 'Mi campo',
    icon: 'M9 4L3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14',
  },
  {
    to: '/calculators',
    label: 'Calculadoras',
    icon: 'M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM8 7h8M8 12h2M14 12h2M8 16h2M14 16h2',
  },
  {
    to: '/tracking',
    label: 'Seguimiento',
    icon: 'M4 20V4M4 20h16M8 16l4-5 3 3 5-6',
  },
]
</script>

<template>
  <nav class="app-nav" aria-label="Secciones">
    <details
      ref="accountMenu"
      class="brand"
      @focusout="onFocusOut"
      @keydown.esc="closeMenu"
    >
      <summary aria-label="Menú de cuenta">
        <img :src="appIcon" alt="" width="32" height="32" />
        <span>Calculadora ganadera</span>
      </summary>
      <div class="account-menu">
        <button type="button" :disabled="loggingOut" @click="signOut">
          {{ loggingOut ? 'Cerrando sesión…' : 'Cerrar sesión' }}
        </button>
        <p v-if="logoutError" role="alert">{{ logoutError }}</p>
      </div>
    </details>
    <RouterLink v-for="item in items" :key="item.to" :to="item.to" class="nav-link">
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        <path
          :d="item.icon"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
/* Celular: barra fija abajo */
.app-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 10;
}

.brand {
  position: relative;
  align-self: center;
  padding: 8px;
}

.brand summary {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  list-style: none;
  font-weight: 700;
  color: var(--color-text);
}

.brand summary::-webkit-details-marker {
  display: none;
}

.brand summary span {
  display: none;
}

.account-menu {
  position: absolute;
  bottom: 100%;
  left: 8px;
  width: 210px;
  padding: 8px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgb(0 0 0 / 12%);
}

.account-menu button {
  width: 100%;
  padding: 10px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.account-menu button:hover {
  background: var(--color-hover);
}

.account-menu button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.account-menu p {
  margin: 8px;
  font-size: 0.85rem;
}

.nav-link {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-decoration: none;
}

.nav-link.router-link-exact-active {
  color: var(--color-primary);
  font-weight: 600;
}

/* Computadora: menú lateral */
@media (min-width: 768px) {
  .app-nav {
    top: 0;
    right: auto;
    width: var(--sidebar-width);
    flex-direction: column;
    gap: 4px;
    padding: 16px 12px;
    border-top: none;
    border-right: 1px solid var(--color-border);
  }

  .brand {
    align-self: stretch;
    padding: 0 8px 20px;
  }

  .brand summary span {
    display: inline;
  }

  .account-menu {
    top: calc(100% - 12px);
    bottom: auto;
  }

  .nav-link {
    flex: none;
    flex-direction: row;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 0.95rem;
  }

  .nav-link:hover {
    background: var(--color-hover);
  }

  .nav-link.router-link-exact-active {
    background: var(--color-primary-soft);
  }
}
</style>
