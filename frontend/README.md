Aplicación web progresiva (PWA).

Vue 3 + Vite + TypeScript, con Pinia, Vue Router, vite-plugin-pwa y Vitest.

## Requisitos

Con `docker compose up` desde la raíz del repositorio, la app queda en http://localhost:5173 sin instalaciones adicionales.

Para trabajar fuera de Docker hace falta Node 24 (la misma versión que usa el CI). Con versiones anteriores a 22.19 las pruebas no arrancan.

## Comandos

Dentro de `frontend/`:

| Comando | Qué hace |
|---|---|
| `npm install` | Instala las dependencias |
| `npm run dev` | Levanta la app en http://localhost:5173 |
| `npm run lint` | Revisa el código con eslint |
| `npm run format` | Da formato al código con prettier |
| `npm run format:check` | Verifica el formato sin modificar archivos (lo usa el CI) |
| `npm run type-check` | Revisa los tipos |
| `npm run test:unit` | Corre las pruebas |
| `npm run build` | Arma la versión para publicar en `dist/` |

## Estructura

```
src/
  main.ts         arranque de la app
  App.vue         estructura general: navegación y contenido
  router/         rutas de cada sección
  views/          una pantalla por sección
  components/     piezas reutilizables, como la navegación
  stores/         estado compartido (Pinia)
  api/            pedidos al backend
  assets/         estilos globales
public/           íconos de la PWA
```

Los pedidos al backend van a `/api/...`. En desarrollo, Vite los reenvía al backend (`vite.config.ts`): a http://localhost:8000, o a la dirección de `API_PROXY_TARGET` si está definida, como pasa en Docker.

Los íconos de la PWA salen de `public/icon.svg`. Si cambia el ícono, se regeneran con:

```
npx @vite-pwa/assets-generator --preset minimal-2023 public/icon.svg
```
