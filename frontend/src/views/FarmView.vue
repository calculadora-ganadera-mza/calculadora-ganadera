<script setup lang="ts">
import { ref } from 'vue'
import ScenarioForm from '@/components/ScenarioForm.vue'
import type { ScenarioRead } from '@/api/scenarios'

const created = ref<ScenarioRead | null>(null)
</script>

<template>
  <section>
    <h1>Mi campo</h1>
    <template v-if="created">
      <p role="status">
        Se registró el establecimiento «{{ created.name }}» con su primera campaña.
      </p>
    </template>
    <template v-else>
      <p>Registrá tu establecimiento para empezar a cargar sus sectores y campañas.</p>
      <ScenarioForm @created="created = $event" />
    </template>
  </section>
</template>
