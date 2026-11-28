<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { AuthError, login, register } from '../api/auth'

const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const name = ref('')
const creating = ref(false)
const busy = ref(false)
const error = ref('')
const resetNotice = ref(route.query.reset === '1')

watch(
  () => route.query.reset,
  (value) => {
    resetNotice.value = value === '1'
  },
)

// Campos del registro, para decir cuál revisar
const FIELDS: Record<string, string> = {
  name: 'el nombre y apellido',
  email: 'el correo electrónico',
  password: 'la contraseña',
}

function registerError(err: unknown): string {
  if (err instanceof AuthError && err.status === 409) return 'Ya existe una cuenta con ese correo.'
  if (err instanceof AuthError && err.status === 422) {
    const field = err.field && FIELDS[err.field]
    return field ? `Revisar ${field}.` : 'Revisar los datos de la cuenta.'
  }
  return 'No se pudo crear la cuenta. Volver a intentar.'
}

// La pestaña del navegador dice en qué formulario se está
watch(
  () => creating.value,
  (value) => {
    document.title = value ? 'Crear cuenta' : 'Iniciar sesión'
  },
)

function toggleMode() {
  creating.value = !creating.value
  error.value = ''
  resetNotice.value = false
}

async function submit() {
  busy.value = true
  error.value = ''
  resetNotice.value = false
  try {
    if (creating.value) {
      await register({
        name: name.value,
        email: email.value,
        password: password.value,
      })
    } else {
      await login(email.value, password.value)
    }
    await router.replace('/')
  } catch (err) {
    error.value = creating.value
      ? registerError(err)
      : 'No se pudo iniciar sesión. Revisar el correo y la contraseña.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="auth-form">
    <h1>{{ creating ? 'Crear cuenta' : 'Iniciar sesión' }}</h1>
    <form @submit.prevent="submit">
      <p v-if="!creating && resetNotice" class="notice" role="status">
        La contraseña se actualizó. Ya se puede ingresar con la nueva.
      </p>
      <template v-if="creating">
        <label
          >Nombre y apellido<input
            v-model="name"
            autocomplete="name"
            required
            minlength="2"
            maxlength="50"
        /></label>
      </template>
      <label
        >Correo electrónico<input v-model="email" type="email" autocomplete="username" required
      /></label>
      <label
        >Contraseña<input
          v-model="password"
          type="password"
          :autocomplete="creating ? 'new-password' : 'current-password'"
          required
          minlength="8"
          maxlength="100"
          :aria-describedby="creating ? 'password-hint' : undefined"
      /></label>
      <p v-if="creating" id="password-hint" class="hint">Mínimo 8 caracteres.</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <button :disabled="busy" type="submit">
        {{ busy ? 'Un momento…' : creating ? 'Crear cuenta' : 'Ingresar' }}
      </button>
      <button :disabled="busy" type="button" @click="toggleMode">
        {{ creating ? 'Ya tengo cuenta' : 'Crear una cuenta' }}
      </button>
      <RouterLink v-if="!creating" to="/forgot-password" class="forgot-link">
        Olvidé mi contraseña
      </RouterLink>
    </form>
  </section>
</template>

<style scoped>
.auth-form {
  max-width: 400px;
  margin: 32px auto;
}
form,
label {
  display: grid;
  gap: 8px;
}
form {
  gap: 16px;
}
input,
button {
  font: inherit;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text);
  background: var(--color-surface);
}
button {
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: wait;
}
[role='alert'] {
  color: var(--color-danger);
}
.notice {
  margin: 0;
  color: var(--color-success);
}
.hint {
  margin: -8px 0 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
.forgot-link {
  justify-self: center;
  color: var(--color-primary);
  font-size: 0.9rem;
}
</style>
