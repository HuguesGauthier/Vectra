<template>
  <q-input outlined v-model="model" :label="label" :readonly="isElectron" class="cursor-pointer">
    <template v-slot:append>
      <q-icon name="folder_open" />
    </template>
  </q-input>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// --- PROPS & MODEL ---
defineProps<{
  label?: string;
}>();

const model = defineModel<string>({ required: false });

// --- STATE ---
const isElectron = computed(() => {
  return window.electronAPI !== undefined;
});
</script>
