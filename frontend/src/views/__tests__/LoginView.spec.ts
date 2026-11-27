import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import LoginView from '../LoginView.vue'
import { AuthError, login, register } from '@/api/auth'

vi.mock('@/api/auth', async (original) => ({
  ...(await original<typeof import('@/api/auth')>()),
  login: vi.fn(),
  register: vi.fn(),
}))

async function open() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/:other(.*)', component: { render: () => null } },
    ],
  })
  await router.push('/login')
  const wrapper = mount(LoginView, { global: { plugins: [router] } })
  return { router, wrapper }
}

// Pasa a crear cuenta y la envía con datos completos
async function createAccount(wrapper: Awaited<ReturnType<typeof open>>['wrapper']) {
  await wrapper.findAll('button[type="button"]')[0]!.trigger('click')
  const [name, email, password] = wrapper.findAll('input')
  await name!.setValue('Ana Pérez')
  await email!.setValue('ana@example.com')
  await password!.setValue('clave-segura')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  vi.resetAllMocks()
  document.title = 'Iniciar sesión'
})

describe('Iniciar sesión y crear cuenta', () => {
  it('al pasar a crear cuenta cambia la pestaña y muestra la ayuda de la contraseña', async () => {
    const { wrapper } = await open()
    expect(wrapper.find('#password-hint').exists()).toBe(false)

    await wrapper.findAll('button[type="button"]')[0]!.trigger('click')

    expect(document.title).toBe('Crear cuenta')
    expect(wrapper.get('#password-hint').text()).toBe('Mínimo 8 caracteres.')
    expect(wrapper.get('input[type="password"]').attributes('aria-describedby')).toBe(
      'password-hint',
    )
  })

  it('si el correo ya tiene una cuenta, lo dice', async () => {
    vi.mocked(register).mockRejectedValue(new AuthError(409))
    const { wrapper } = await open()

    await createAccount(wrapper)

    expect(wrapper.get('[role="alert"]').text()).toBe('Ya existe una cuenta con ese correo.')
  })

  it('si un dato no es válido, dice qué campo revisar', async () => {
    vi.mocked(register).mockRejectedValue(new AuthError(422, 'email'))
    const { wrapper } = await open()

    await createAccount(wrapper)

    expect(wrapper.get('[role="alert"]').text()).toBe('Revisar el correo electrónico.')
  })

  it('si no pudo iniciar sesión, pide revisar el correo y la contraseña', async () => {
    vi.mocked(login).mockRejectedValue(new AuthError(401))
    const { wrapper } = await open()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(
      'No se pudo iniciar sesión. Revisar el correo y la contraseña.',
    )
  })
})
