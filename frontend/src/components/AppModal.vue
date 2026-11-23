<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useId } from 'vue'

defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()

const titleId = useId()
const box = ref<HTMLElement>()
// Lo que tenía el foco antes de abrir; lo recupera al cerrar
let previousFocus: HTMLElement | null = null

function focusables(): HTMLElement[] {
  const items = box.value?.querySelectorAll<HTMLElement>('a[href], button, input, select, textarea')
  return [...(items ?? [])].filter((item) => !item.hasAttribute('disabled'))
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
  if (event.key !== 'Tab') return
  // Con Tab el foco da la vuelta dentro de la ventana y no se va a la pantalla de atrás
  const items = focusables()
  const first = items[0]
  const last = items[items.length - 1]
  if (!first || !last) return
  const active = document.activeElement
  if (!box.value?.contains(active)) {
    event.preventDefault()
    first.focus()
  } else if (event.shiftKey && active === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  previousFocus = document.activeElement as HTMLElement | null
  document.addEventListener('keydown', onKey)
  // El foco entra en el primer campo o, si no hay, en el primer botón del contenido (no en la cruz)
  const target =
    box.value?.querySelector<HTMLElement>('input, select') ??
    box.value?.querySelector<HTMLElement>(':scope > :not(header) button')
  target?.focus()
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  previousFocus?.focus()
})
</script>

<template>
  <Teleport to="body">
    <!-- mousedown: si se arrastra una selección desde adentro hacia afuera, la ventana no se cierra -->
    <div class="backdrop" @mousedown.self="emit('close')">
      <div ref="box" class="modal" role="dialog" aria-modal="true" :aria-labelledby="titleId">
        <header>
          <h2 :id="titleId">{{ title }}</h2>
          <button type="button" class="close" aria-label="Cerrar" @click="emit('close')">×</button>
        </header>
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(0 0 0 / 40%);
}

.modal {
  width: min(440px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  background: var(--color-surface);
  border-radius: 12px;
  box-shadow: 0 8px 30px rgb(0 0 0 / 25%);
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

h2 {
  margin: 0;
  font-size: 1.1rem;
}

.close {
  border: 0;
  background: none;
  color: var(--color-text-muted);
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
}
</style>
