<template>
  <div class="row justify-center full-width">
    <div class="col-md-12">
      <div v-if="!hideTitle">
        <div class="text-center q-mb-lg text-subtitle1">
          {{ $t('retrievalStrategyDesc') }}
        </div>
      </div>

      <div class="row justify-center">
        <div class="col-10">
          <RetrievalParams v-model="localData" hide-title :providers="providers" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Assistant } from 'src/services/assistantService';
import type { ProviderOption } from 'src/models/ProviderOption';
import RetrievalParams from '../RetrievalParams.vue';

defineOptions({
  name: 'AssistantRetrievalStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  providers: ProviderOption[];
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});
</script>
