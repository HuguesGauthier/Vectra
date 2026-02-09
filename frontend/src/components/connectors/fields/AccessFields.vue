<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs">{{ $t('accessControl') }}</div>
    <div class="text-caption text-grey-6 q-mb-md">{{ $t('accessControlDesc') }}</div>

    <q-select
      :model-value="aclArray"
      @update:model-value="updateAcl"
      :label="$t('connectorAcl')"
      :hint="$t('connectorAclHint')"
      use-input
      use-chips
      multiple
      dark
      color="white"
      standout
      input-debounce="0"
      @new-value="createValue"
      :rules="[(val) => (val && val.length > 0) || $t('aclTagRequired')]"
    >
      <template v-slot:selected-item="scope">
        <q-chip
          removable
          @remove="scope.removeAtIndex(scope.index)"
          :tabindex="scope.tabindex"
          color="accent"
          text-color="grey-3"
          size="md"
        >
          {{ scope.opt }}
        </q-chip>
      </template>
    </q-select>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// --- DEFINITIONS ---
const modelValue = defineModel<string[] | string>({ required: true });

// --- COMPUTED ---
const aclArray = computed(() => {
  if (Array.isArray(modelValue.value)) {
    return modelValue.value;
  }
  if (typeof modelValue.value === 'string') {
    try {
      const parsed = JSON.parse(modelValue.value);
      return Array.isArray(parsed) ? parsed : [modelValue.value];
    } catch {
      return modelValue.value ? [modelValue.value] : [];
    }
  }
  return [];
});

// --- FUNCTIONS ---
function updateAcl(value: string[]) {
  modelValue.value = value;
}

function createValue(val: string, done: (item?: string) => void) {
  if (val.length > 0) {
    const trimmed = val.trim();
    if (trimmed && !aclArray.value.includes(trimmed)) {
      done(trimmed);
      return;
    }
  }
  done();
}
</script>
