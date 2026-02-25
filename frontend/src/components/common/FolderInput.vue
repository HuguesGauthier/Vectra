<template>
  <q-input
    outlined
    v-model="model"
    :label="label"
    :readonly="isElectron"
    class="cursor-pointer"
    @click="pickFolder"
  >
    <template v-slot:append>
      <q-icon name="folder_open" class="cursor-pointer" @click="pickFolder" />
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

// --- FUNCTIONS ---
async function pickFolder() {
  if (isElectron.value && window.electronAPI) {
    const path = await window.electronAPI.selectFolder();
    if (path) {
      model.value = path;
    }
  }
}
</script>
