<template>
  <div class="row q-col-gutter-sm">
    <div v-for="option in options" :key="option.value" class="col-12 col-sm-4">
      <div
        class="selection-card cursor-pointer q-pa-md relative-position full-height transition-generic"
        :class="{ active: modelValue === option.value }"
        @click="$emit('update:modelValue', option.value)"
        v-ripple
      >
        <div class="row items-center no-wrap">
          <q-icon v-if="option.icon" :name="option.icon" size="24px" class="q-mr-md" />
          <div class="col">
            <div class="text-weight-bold">
              {{ option.label }}
            </div>
            <div v-if="option.description" class="text-caption" style="line-height: 1.2">
              {{ option.description }}
            </div>
          </div>

          <div v-if="modelValue === option.value">
            <q-icon name="check_circle" color="accent" size="20px" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';

export interface SelectionOption {
  label: string;
  value: string;
  icon?: string;
  description?: string;
}

defineProps({
  modelValue: {
    type: String as PropType<string | undefined>,
    default: '',
  },
  options: {
    type: Array as PropType<SelectionOption[]>,
    default: () => [],
  },
});

defineEmits(['update:modelValue']);
</script>

<style scoped>
.selection-card {
  border: 1px solid var(--q-third);
  border-radius: 12px;
  background: var(--q-primary);
}

.selection-card:hover {
  background: var(--q-primary);
  border-color: var(--q-accent);
}

.selection-card.active {
  background: var(--q-accent);
  border-color: var(--q-accent);
  color: var(--q-primary);
}

.transition-generic {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
}
</style>
