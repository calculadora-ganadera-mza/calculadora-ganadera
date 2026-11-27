import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'

import ForgotPasswordView from '../ForgotPasswordView.vue'
import { routes } from '@/router'
import { requestPasswordReset, resetPassword } from '@/api/auth'
import { ApiError } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/auth', () => ({
  requestPasswordReset: vi.fn(),
  resetPassword: vi.fn(),
}))

async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push('/forgot-password')
  await router.isReady()
  const wrapper = mount(ForgotPasswordView, { global: { plugins: [pinia, router] } })
  return { wrapper, router }
}

beforeEach(() => vi.resetAllMocks())

describe('ForgotPasswordView', () => {
  it('pide el código por correo y muestra los campos de cambio en la misma pantalla', async () => {
    const { wrapper } = await mountView()

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(requestPasswordReset).toHaveBeenCalledWith('ana@example.com')
    expect(wrapper.find('[role="status"]').text()).toContain('6 dígitos')

    const codeInput = wrapper.find('input[autocomplete="one-time-code"]')
    const passwordInput = wrapper.find('input[autocomplete="new-password"]')
    expect(codeInput.attributes('inputmode')).toBe('numeric')
    expect(passwordInput.attributes('minlength')).toBe('8')
    expect(passwordInput.attributes('maxlength')).toBe('100')
  })

  it('no envía un código que no tiene 6 dígitos', async () => {
    const { wrapper } = await mountView()
    await wrapper.find('button[type="button"]').trigger('click')

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('12345')
    await wrapper.find('input[autocomplete="new-password"]').setValue('new-password-456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe('El código tiene 6 dígitos.')
    expect(resetPassword).not.toHaveBeenCalled()
  })

  it('muestra el error del backend cuando el código no sirve', async () => {
    vi.mocked(resetPassword).mockRejectedValue(
      new ApiError('El código no es válido. Revisalo o pedí uno nuevo.'),
    )
    const { wrapper } = await mountView()
    await wrapper.find('button[type="button"]').trigger('click')

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await wrapper.find('input[autocomplete="new-password"]').setValue('new-password-456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe(
      'El código no es válido. Revisalo o pedí uno nuevo.',
    )
  })

  it('cambia la contraseña sin iniciar sesión y vuelve a /login', async () => {
    const { wrapper, router } = await mountView()
    await wrapper.find('button[type="button"]').trigger('click')

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await wrapper.find('input[autocomplete="new-password"]').setValue('new-password-456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(resetPassword).toHaveBeenCalledWith({
      email: 'ana@example.com',
      code: '123456',
      password: 'new-password-456',
    })
    expect(useAuthStore().isAuthenticated).toBe(false)
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/login'))
  })

  it('limpia un error previo al pasar a «Ya tengo un código»', async () => {
    vi.mocked(requestPasswordReset).mockRejectedValue(new Error('Error 422'))
    const { wrapper } = await mountView()

    await wrapper.find('input[type="email"]').setValue('ana@b')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toBe(
      'No se pudo pedir el código. Revisá el correo e intentá de nuevo.',
    )

    await wrapper.find('button[type="button"]').trigger('click')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('muestra «Enviando…» solo en el botón de reenvío mientras pide otro código', async () => {
    let resolveResend!: () => void
    vi.mocked(requestPasswordReset).mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveResend = resolve
        }),
    )
    const { wrapper } = await mountView()
    await wrapper.find('button[type="button"]').trigger('click')

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    const submitButton = wrapper.find('button[type="submit"]')
    const resendButton = wrapper.find('button[type="button"]')
    await resendButton.trigger('click')

    expect(resendButton.text()).toBe('Enviando…')
    expect(submitButton.text()).toBe('Cambiar contraseña')
    expect((resendButton.element as HTMLButtonElement).disabled).toBe(true)
    expect((submitButton.element as HTMLButtonElement).disabled).toBe(true)

    resolveResend()
    await flushPromises()
    expect(resendButton.text()).toBe('Enviar otro código')
    expect((submitButton.element as HTMLButtonElement).disabled).toBe(false)
  })

  it('valida el correo antes de «Enviar otro código»', async () => {
    const { wrapper } = await mountView()
    await wrapper.find('button[type="button"]').trigger('click')

    // Con el correo vacío o malformado no debe llamar a la API.
    const resendButton = wrapper.find('button[type="button"]')
    await resendButton.trigger('click')
    await flushPromises()
    expect(requestPasswordReset).not.toHaveBeenCalled()

    await wrapper.find('input[type="email"]').setValue('mal')
    await resendButton.trigger('click')
    await flushPromises()
    expect(requestPasswordReset).not.toHaveBeenCalled()

    await wrapper.find('input[type="email"]').setValue('ana@example.com')
    await resendButton.trigger('click')
    await flushPromises()
    expect(requestPasswordReset).toHaveBeenCalledWith('ana@example.com')
  })
})
