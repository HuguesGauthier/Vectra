<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs">{{ $t('generalInformation') }}</div>

    <q-input
      :model-value="modelValue.name"
      @update:model-value="(val) => updateName(String(val || ''))"
      :label="$t('name')"
      color="white"
      standout
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.description"
      @update:model-value="(val) => updateDescription(String(val || ''))"
      :label="$t('description')"
      color="white"
      standout
      type="textarea"
      rows="3"
    />
  </div>
</template>

<script setup lang="ts">
// --- DEFINITIONS ---
interface GeneralConfig {
  name: string;
  description: string | undefined;
}

const modelValue = defineModel<GeneralConfig>({ required: true });

// --- FUNCTIONS ---
function updateName(value: string) {
  modelValue.value = { ...modelValue.value, name: value };
}

function updateDescription(value: string) {
  modelValue.value = { ...modelValue.value, description: value };
}
</script>
