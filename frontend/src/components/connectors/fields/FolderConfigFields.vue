<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs q-mt-lg">{{ $t('folderConfiguration') }}</div>

    <FolderInput
      :model-value="modelValue.path || ''"
      @update:model-value="updateField('path', $event)"
      :label="$t('folderPath')"
      color="white"
      standout
      lazy-rules
      :rules="[(val: string | null | undefined) => !!val || $t('fieldRequired')]"
    />

    <q-toggle
      :model-value="!!modelValue.recursive"
      @update:model-value="updateField('recursive', $event)"
      :label="$t('recursive')"
      color="accent"
      dense
    />
  </div>
</template>

<script setup lang="ts">
import FolderInput from 'components/common/FolderInput.vue';

// --- DEFINITIONS ---
interface FolderConfig {
  path?: string;
  recursive?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

const modelValue = defineModel<FolderConfig>({ required: true });

// --- FUNCTIONS ---
function updateField(
  field: keyof FolderConfig,
  value: string | number | boolean | null | undefined,
) {
  modelValue.value = { ...modelValue.value, [field]: value };
}
</script>
