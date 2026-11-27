/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

import 'vue-router'

// Datos extra de cada ruta
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    // Accesible sin iniciar sesión; con sesión iniciada redirige a Inicio
    public?: boolean
    // Solo la ven los administradores
    adminOnly?: boolean
  }
}
