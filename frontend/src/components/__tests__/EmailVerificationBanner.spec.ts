import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import EmailVerificationBanner from '../EmailVerificationBanner.vue'
import { ApiError } from '@/api/errors'
import { loadCurrentUser, resendVerification, verifyEmail } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/users', () => ({
  loadCurrentUser: vi.fn(),
  resendVerification: vi.fn(),
  verifyEmail: vi.fn(),
}))

const user = (emailVerified: boolean) => ({
  id: 1,
  name: 'Ana',
  email: 'ana@example.com',
  role: 'producer' as const,
  email_verified: emailVerified,
})

function mountWith(emailVerified = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = user(emailVerified)
  return mount(EmailVerificationBanner, { global: { plugins: [pinia] } })
}

async function submitCode(wrapper: ReturnType<typeof mountWith>, code: string) {
  await wrapper.find('input').setValue(code)
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => vi.resetAllMocks())

describe('EmailVerificationBanner', () => {
  it('no se muestra con el correo verificado', () => {
    expect(mountWith(true).find('.verification').exists()).toBe(false)
  })

  it('verifica el correo y desaparece al leer el usuario actualizado', async () => {
    vi.mocked(loadCurrentUser).mockImplementation(async () => {
      useAuthStore().user = user(true)
    })
    const wrapper = mountWith()
    expect(wrapper.text()).toContain('ana@example.com')

    await submitCode(wrapper, '123456')

    expect(verifyEmail).toHaveBeenCalledWith('123456')
    expect(wrapper.find('.verification').exists()).toBe(false)
  })

  it('no manda un código que no tiene 6 dígitos', async () => {
    const wrapper = mountWith()

    await submitCode(wrapper, '12345')

    expect(wrapper.text()).toContain('El código tiene 6 dígitos.')
    expect(verifyEmail).not.toHaveBeenCalled()
  })

  it('muestra el mensaje del backend si el código no sirve', async () => {
    vi.mocked(verifyEmail).mockRejectedValue(new ApiError('El código no es correcto.'))
    const wrapper = mountWith()

    await submitCode(wrapper, '123456')

    expect(wrapper.find('[role="alert"]').text()).toBe('El código no es correcto.')
    expect(loadCurrentUser).not.toHaveBeenCalled()
  })

  it('pide un código nuevo', async () => {
    const wrapper = mountWith()

    await wrapper.find('button[type="button"]').trigger('click')
    await flushPromises()

    expect(resendVerification).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Se envió un código nuevo.')
  })
})
