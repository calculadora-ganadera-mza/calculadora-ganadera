<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchHealth, type HealthStatus } from '@/api/health'

const status = ref<HealthStatus | 'checking'>('checking')

const messages = {
  checking: 'Revisando la conexión…',
  ok: 'El servidor responde.',
  database_unavailable: 'El servidor responde, pero no llega a la base de datos.',
  offline: 'No hay conexión con el servidor.',
}

async function check() {
  status.value = 'checking'
  status.value = await fetchHealth()
}

onMounted(check)
</script>

<template>
  <div class="server-status" :class="status" role="status">
    <span class="dot" aria-hidden="true"></span>
    <span class="message">{{ messages[status] }}</span>
    <button v-if="status !== 'ok' && status !== 'checking'" type="button" @click="check">
      Reintentar
    </button>
  </div>
</template>

<style scoped>
.server-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-text-muted);
  flex-shrink: 0;
}

.ok .dot {
  background: var(--color-success);
}

.database_unavailable .dot,
.offline .dot {
  background: var(--color-danger);
}

.message {
  flex: 1;
}

button {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}
</style>
