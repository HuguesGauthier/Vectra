<template>
  <div class="row q-col-gutter-lg" :class="{ 'justify-center': center }">
    <div v-for="provider in providers" :key="provider.id" :class="gridCols">
      <AiProviderCard
        v-bind="provider"
        :disabled="forceEnabled ? false : provider.disabled"
        :selected="modelValue === provider.id"
        :selectable="selectable"
        :compact="compact"
        :show-config="showConfig"
        @click="handleSelect(provider.id)"
        @configure="$emit('configure', provider.id)"
      >
        <!-- Re-expose slots if needed -->
        <template v-if="$slots.actions" #actions>
          <slot name="actions" :provider="provider" />
        </template>
      </AiProviderCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProviderOption } from 'src/models/ProviderOption';
import AiProviderCard from './AiProviderCard.vue';

/**
 * AiProviderGrid.vue
 * A layout component for rendering a list of AI providers using AiProviderCard.
 */

defineOptions({
  name: 'AiProviderGrid',
});

const props = defineProps<{
  modelValue?: string | undefined;
  providers: ProviderOption[];
  selectable?: boolean;
  compact?: boolean;
  showConfig?: boolean;
  center?: boolean;
  gridCols?: string;
  forceEnabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void;
  (e: 'configure', providerId: string): void;
}>();

function handleSelect(id: string) {
  if (props.selectable) {
    emit('update:modelValue', id);
  } else if (props.showConfig) {
    // In configuration mode (like Settings), clicking the card should also open config
    emit('configure', id);
  }
}
</script>
