<template>
  <div class="row justify-center max-width-container">
    <div class="col-12 col-md-11">
      <AiProviderGrid
        v-model="localData.model"
        :providers="aiModels"
        selectable
        grid-cols="col-12 col-sm-6 col-md-3"
        @configure="showAdvancedParams = true"
      />

      <!-- Advanced Params Dialog -->
      <AdvancedLLMParams
        v-if="localData.configuration"
        v-model="showAdvancedParams"
        v-model:configuration="localData.configuration"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { ProviderOption } from 'src/models/ProviderOption';
import type { Assistant } from 'src/services/assistantService';
import AdvancedLLMParams from '../AdvancedLLMParams.vue';
import AiProviderGrid from 'src/components/common/AiProviderGrid.vue';

defineOptions({
  name: 'AssistantIntelligenceStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  providers: ProviderOption[];
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

const showAdvancedParams = ref(false);

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

// AI Models - map from centralized chat providers
const aiModels = computed(() => {
  // Sort to put Ollama first
  return [...props.providers].sort((a, b) => {
    if (a.value === 'ollama') return -1;
    if (b.value === 'ollama') return 1;
    return 0;
  });
});
</script>

<style scoped>
.max-width-container {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
