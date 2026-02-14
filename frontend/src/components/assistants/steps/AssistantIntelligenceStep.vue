<template>
  <div class="row justify-center max-width-container">
    <div class="col-12 col-md-10">
      <div class="row q-col-gutter-lg justify-center">
        <div v-for="model in aiModels" :key="model.value" class="col-12 col-sm-6 col-md-4">
          <q-card
            class="selection-card cursor-pointer full-height q-pa-md"
            :class="{ selected: localData.model === model.value }"
            v-ripple
            @click="localData.model = model.value || ''"
          >
            <q-card-section class="column items-center text-center">
              <q-avatar size="60px" :color="model.color" text-color="white" class="q-mb-md">
                <q-icon :name="model.icon" />
              </q-avatar>
              <div class="text-h6">{{ model.label }}</div>
              <div class="text-caption q-mt-sm">{{ model.description }}</div>

              <q-btn
                v-if="localData.model === model.value"
                flat
                :label="$t('configureAdvancedParams')"
                icon="settings"
                color="accent"
                class="q-mt-md full-width"
                outline
                size="sm"
                @click.stop="showAdvancedParams = true"
              />
            </q-card-section>
            <div v-if="localData.model === model.value" class="selected-overlay">
              <q-icon name="check_circle" color="accent" size="32px" />
            </div>
          </q-card>
        </div>
      </div>

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
import { useI18n } from 'vue-i18n';
import { useAiProviders } from 'src/composables/useAiProviders';
import type { Assistant } from 'src/services/assistantService';
import AdvancedLLMParams from '../AdvancedLLMParams.vue';

defineOptions({
  name: 'AssistantIntelligenceStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

const { t } = useI18n();
const { chatProviderOptions } = useAiProviders();

const showAdvancedParams = ref(false);

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

// AI Models - map from centralized chat providers
const aiModels = computed(() => {
  return chatProviderOptions.value.map((provider) => {
    if (provider.value === 'gemini') {
      return {
        value: provider.value,
        label: provider.label,
        description: t('geminiDesc'),
        icon: 'auto_awesome',
        color: 'blue-6',
      };
    } else if (provider.value === 'openai') {
      return {
        value: provider.value,
        label: provider.label,
        description: t('openaiDesc'),
        icon: 'smart_toy',
        color: 'green-6',
      };
    } else if (provider.value === 'mistral') {
      return {
        value: provider.value,
        label: provider.label,
        description: t('mistralDesc'),
        icon: 'air',
        color: 'orange-10', // Mistral branding is often warm
      };
    } else if (provider.value === 'ollama') {
      return {
        value: provider.value,
        label: provider.label,
        description: t('mistralLocalDesc'),
        icon: 'terminal',
        color: 'blue-grey-8',
      };
    }
    return {
      value: provider.value || '',
      label: provider.label,
      description: '',
      icon: 'psychology',
      color: 'grey-6',
    };
  });
});
</script>

<style scoped>
.selection-card {
  transition: all 0.3s ease;
  background: var(--q-secondary);
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--q-sixth);
}

.selection-card:hover {
  transform: translateY(-5px);
  background: rgba(255, 255, 255, 0.08);
}

.selection-card.selected {
  border-color: var(--q-accent);
  background: var(--q-secondary);
}

.selected-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
