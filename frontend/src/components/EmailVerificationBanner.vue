<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError } from '@/api/errors'
import { loadCurrentUser, resendVerification, verifyEmail } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const { user } = storeToRefs(useAuthStore())
const code = ref('')
// Pedido en curso: mientras dura, los dos botones quedan deshabilitados
const pending = ref<'verify' | 'resend' | null>(null)
const error = ref('')
const sent = ref(false)

async function verify() {
  error.value = ''
  sent.value = false
  if (!/^\d{6}$/.test(code.value)) {
    error.value = 'El código tiene 6 dígitos.'
    return
  }
  pending.value = 'verify'
  try {
    await verifyEmail(code.value)
    // Con el usuario actualizado, el aviso desaparece
    await loadCurrentUser()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo verificar el correo.'
  } finally {
    pending.value = null
  }
}

async function resend() {
  error.value = ''
  sent.value = false
  pending.value = 'resend'
  try {
    await resendVerification()
    code.value = ''
    sent.value = true
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'No se pudo enviar el código.'
  } finally {
    pending.value = null
  }
}
</script>

<template>
  <section
    v-if="user && !user.email_verified"
    class="verification"
    aria-label="Verificación del correo"
  >
    <p>
      <strong>Falta verificar el correo {{ user.email }}.</strong>
      Hay que escribir el código de 6 dígitos que llegó a ese correo.
    </p>
    <form class="row" novalidate @submit.prevent="verify">
      <label for="verification-code">Código</label>
      <input
        id="verification-code"
        v-model.trim="code"
        type="text"
        inputmode="numeric"
        autocomplete="one-time-code"
        maxlength="6"
      />
      <button class="btn btn-primary" type="submit" :disabled="pending !== null">
        {{ pending === 'verify' ? 'Verificando…' : 'Verificar' }}
      </button>
      <button class="text-button" type="button" :disabled="pending !== null" @click="resend">
        {{ pending === 'resend' ? 'Enviando…' : 'Enviar un código nuevo' }}
      </button>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="sent" class="sent" role="status">Se envió un código nuevo.</p>
  </section>
</template>

<style scoped>
.verification {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.verification p {
  margin: 0;
}

.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

label {
  font-weight: 600;
}

input {
  width: 120px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  letter-spacing: 0.15em;
}

.text-button:disabled {
  opacity: 0.6;
  cursor: default;
}

.sent {
  color: var(--color-success);
}
</style>
