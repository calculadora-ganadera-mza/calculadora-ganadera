<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../api/auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const name = ref('')
const creating = ref(false)
const busy = ref(false)
const error = ref('')

function toggleMode() {
  creating.value = !creating.value
  error.value = ''
}

async function submit() {
  busy.value = true
  error.value = ''
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
  } catch {
    error.value = creating.value
      ? 'No se pudo crear la cuenta. Revisá los datos o intentá con otro correo.'
      : 'No se pudo iniciar sesión. Revisá tu correo y contraseña.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="auth-form">
    <h1>{{ creating ? 'Crear cuenta' : 'Iniciar sesión' }}</h1>
    <form @submit.prevent="submit">
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
      /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button :disabled="busy" type="submit">
        {{ busy ? 'Un momento…' : creating ? 'Crear cuenta' : 'Ingresar' }}
      </button>
      <button :disabled="busy" type="button" @click="toggleMode">
        {{ creating ? 'Ya tengo cuenta' : 'Crear una cuenta' }}
      </button>
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
</style>
