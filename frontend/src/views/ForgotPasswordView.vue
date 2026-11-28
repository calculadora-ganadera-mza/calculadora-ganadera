<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { requestPasswordReset, resetPassword } from '../api/auth'
import { ApiError } from '../api/errors'

const router = useRouter()
const emailInput = ref<HTMLInputElement>()
const email = ref('')
const code = ref('')
const password = ref('')
const codeSent = ref(false)
// Acción en curso: mientras dura, todos los botones quedan deshabilitados
const pending = ref<'send' | 'reset' | null>(null)
const error = ref('')
const notice = ref('')

function showCodeStep() {
  codeSent.value = true
  error.value = ''
  notice.value = ''
}

async function sendCode() {
  error.value = ''
  notice.value = ''
  if (emailInput.value && !emailInput.value.reportValidity()) return
  if (email.value.length < 5 || email.value.length > 100) {
    error.value = 'El correo no es válido.'
    return
  }
  pending.value = 'send'
  try {
    await requestPasswordReset(email.value)
    codeSent.value = true
    code.value = ''
    notice.value = 'Si el correo tiene una cuenta registrada, enviamos un código de 6 dígitos.'
  } catch (err) {
    error.value =
      err instanceof ApiError
        ? err.message
        : 'No se pudo pedir el código. Revisar el correo y volver a intentar.'
  } finally {
    pending.value = null
  }
}

async function submitReset() {
  error.value = ''
  notice.value = ''
  if (!/^\d{6}$/.test(code.value)) {
    error.value = 'El código tiene 6 dígitos.'
    return
  }
  pending.value = 'reset'
  try {
    await resetPassword({
      email: email.value,
      code: code.value,
      password: password.value,
    })
    await router.replace({ name: 'login', query: { reset: '1' } })
  } catch (err) {
    error.value =
      err instanceof ApiError
        ? err.message
        : 'No se pudo cambiar la contraseña. Revisar los datos y volver a intentar.'
  } finally {
    pending.value = null
  }
}
</script>

<template>
  <section class="auth-form">
    <h1>Recuperar contraseña</h1>
    <p v-if="!codeSent" class="hint">
      Escribir el correo de la cuenta. Si existe, llega un código de 6 dígitos.
    </p>

    <form v-if="!codeSent" @submit.prevent="sendCode">
      <label
        >Correo electrónico<input
          ref="emailInput"
          v-model.trim="email"
          type="email"
          autocomplete="email"
          required
          minlength="5"
          maxlength="100"
      /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button :disabled="pending !== null" type="submit">
        {{ pending === 'send' ? 'Enviando…' : 'Enviar código' }}
      </button>
      <button :disabled="pending !== null" type="button" @click="showCodeStep">
        Ya tengo un código
      </button>
      <RouterLink to="/login" class="back-link">Volver a iniciar sesión</RouterLink>
    </form>

    <form v-else @submit.prevent="submitReset">
      <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      <label
        >Correo electrónico<input
          ref="emailInput"
          v-model.trim="email"
          type="email"
          autocomplete="username"
          required
          minlength="5"
          maxlength="100"
      /></label>
      <label
        >Código de 6 dígitos<input
          v-model.trim="code"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          maxlength="6"
          required
      /></label>
      <label
        >Contraseña nueva<input
          v-model="password"
          type="password"
          autocomplete="new-password"
          required
          minlength="8"
          maxlength="100"
      /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button :disabled="pending !== null" type="submit">
        {{ pending === 'reset' ? 'Guardando…' : 'Cambiar contraseña' }}
      </button>
      <button :disabled="pending !== null" type="button" @click="sendCode">
        {{ pending === 'send' ? 'Enviando…' : 'Enviar otro código' }}
      </button>
      <RouterLink to="/login" class="back-link">Volver a iniciar sesión</RouterLink>
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
.back-link {
  justify-self: center;
  color: var(--color-primary);
  font-size: 0.9rem;
}
</style>
