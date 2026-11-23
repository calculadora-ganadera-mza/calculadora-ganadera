import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import AppModal from '../AppModal.vue'

// Una pantalla con un botón que abre la ventana, para ver a dónde vuelve el foco
const Page = defineComponent({
  setup() {
    const open = ref(false)
    return () => [
      h('button', { id: 'opener', onClick: () => (open.value = true) }, 'Abrir'),
      open.value
        ? h(AppModal, { title: 'Nombre', onClose: () => (open.value = false) }, () => [
            h('input', { id: 'first' }),
            h('button', { id: 'last' }, 'Guardar'),
          ])
        : null,
    ]
  },
})

let wrapper: VueWrapper | undefined

afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

async function openModal() {
  wrapper = mount(Page, { attachTo: document.body })
  const opener = document.getElementById('opener') as HTMLButtonElement
  opener.focus()
  opener.click()
  await wrapper.vm.$nextTick()
  return opener
}

function press(key: string, shiftKey = false) {
  document.dispatchEvent(new KeyboardEvent('keydown', { key, shiftKey, cancelable: true }))
}

describe('AppModal', () => {
  it('pone el foco en el primer campo', async () => {
    await openModal()
    expect(document.activeElement?.id).toBe('first')
    expect(document.querySelector('[role="dialog"]')?.getAttribute('aria-modal')).toBe('true')
  })

  it('con Tab el foco da la vuelta dentro de la ventana', async () => {
    await openModal()
    document.getElementById('last')!.focus()
    press('Tab')
    // La cruz de cerrar es lo primero que se puede enfocar
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Cerrar')
    press('Tab', true)
    expect(document.activeElement?.id).toBe('last')
  })

  it('se cierra con Escape y devuelve el foco a lo que la abrió', async () => {
    const opener = await openModal()
    press('Escape')
    await wrapper!.vm.$nextTick()

    expect(document.querySelector('[role="dialog"]')).toBeNull()
    expect(document.activeElement).toBe(opener)
  })

  it('se cierra al apretar afuera, pero no al apretar adentro', async () => {
    await openModal()
    document.getElementById('first')!.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await wrapper!.vm.$nextTick()
    expect(document.querySelector('[role="dialog"]')).not.toBeNull()

    document
      .querySelector('.backdrop')!
      .dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await wrapper!.vm.$nextTick()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })
})
