<template>
  <div class="row justify-center">
    <div class="col-10">
      <q-input
        v-model="localData.name"
        :label="$t('name')"
        :rules="[(val) => !!val || $t('nameRequired')]"
        outlined
        bg-color="secondary"
        input-class="text-main"
        label-color="sub"
        class="q-mb-md"
      />

      <q-input
        v-model="localData.description"
        :label="$t('description')"
        outlined
        bg-color="secondary"
        input-class="text-main"
        label-color="sub"
        type="textarea"
        rows="3"
        class="q-mb-lg"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Assistant } from 'src/services/assistantService';

defineOptions({
  name: 'AssistantGeneralStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
  (e: 'file-selected', file: File | null): void;
}>();

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});
</script>

<style scoped>
:deep(.q-field--outlined .q-field__control):before {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined .q-field__control):after {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined.q-field--focused .q-field__control):after {
  border-color: var(--q-accent) !important;
  border-width: 1px !important;
}
</style>
