<template>
  <div class="row justify-center max-width-container">
    <div class="col-12 col-md-10">
      <div class="row q-col-gutter-lg justify-center">
        <div v-for="model in aiModels" :key="model.value" class="col-12 col-sm-6 col-md-3">
          <q-card
            class="selection-card full-height q-pa-md"
            :class="{
              selected: localData.model === model.value,
              'disabled-card': model.disabled,
              'cursor-pointer': !model.disabled,
            }"
            v-ripple="!model.disabled"
            @click="!model.disabled && (localData.model = model.value || '')"
          >
            <q-card-section class="column items-center text-center q-pa-sm">
              <div class="q-mb-md relative-position">
                <img
                  :src="model.logo"
                  style="width: 48px; height: 48px; object-fit: contain"
                  :class="{ 'grayscale-filter': model.disabled }"
                />
              </div>
              <div
                class="text-subtitle1 text-weight-bold"
                :class="{ 'text-grey-6': model.disabled }"
              >
                {{ model.label }}
              </div>
              <div
                class="text-caption"
                :class="{ 'text-grey-7': model.disabled }"
                style="line-height: 1.2; font-size: 0.75rem"
              >
                {{ model.description }}
              </div>

              <!-- Not Configured Badge -->
              <div v-if="model.disabled" class="q-mt-sm">
                <q-badge color="grey-9" text-color="grey-4" class="q-pa-xs">
                  <q-icon name="lock" size="10px" class="q-mr-xs" />
                  <span style="font-size: 0.7rem">{{ $t('notConfigured') }}</span>
                </q-badge>
              </div>

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
import { ref, computed, onMounted } from 'vue';
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

onMounted(() => {
  // Set Ollama as default if no model is selected
  if (!localData.value.model) {
    localData.value.model = 'ollama';
  }
});

// AI Models - map from centralized chat providers
const aiModels = computed(() => {
  const models = chatProviderOptions.value.map((provider) => {
    const baseModel = {
      value: provider.value || '',
      label: provider.label,
      description: '',
      logo: provider.logo,
      disabled: provider.disabled,
    };

    if (provider.value === 'gemini') {
      return {
        ...baseModel,
        description: t('geminiDesc'),
        color: 'blue-6',
      };
    } else if (provider.value === 'openai') {
      return {
        ...baseModel,
        description: t('openaiDesc'),
        color: 'green-6',
      };
    } else if (provider.value === 'mistral') {
      return {
        ...baseModel,
        description: t('mistralDesc'),
        color: 'orange-10',
      };
    } else if (provider.value === 'ollama') {
      return {
        ...baseModel,
        description: t('mistralLocalDesc'),
        color: 'blue-grey-8',
      };
    }
    return baseModel;
  });

  // Sort to put Ollama first
  return models.sort((a, b) => {
    if (a.value === 'ollama') return -1;
    if (b.value === 'ollama') return 1;
    return 0;
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

.disabled-card {
  opacity: 0.6;
  filter: grayscale(0.8);
  cursor: not-allowed !important;
  border-style: dashed;
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

.grayscale-filter {
  filter: grayscale(100%);
  opacity: 0.5;
}
</style>
