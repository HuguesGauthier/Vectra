<template>
  <q-dialog v-model="isOpen">
    <q-card class="bg-primary" style="min-width: 500px">
      <q-card-section class="row items-center q-pb-none bg-secondary">
        <div class="text-h6">{{ providerName }} Configuration</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-form @submit="handleSave" class="column q-gutter-y-md">
        <q-card-section class="q-pt-md">
          <!-- Hidden username to satisfy browser heuristics for password forms -->
          <input
            type="text"
            name="username"
            autocomplete="username"
            style="display: none; opacity: 0; position: absolute; left: -9999px"
            tabindex="-1"
          />

          <div class="column q-gutter-y-md">
            <!-- Gemini Chat Configuration -->
            <template v-if="providerId === 'gemini'">
              <div class="text-subtitle2 q-mb-sm">{{ $t('geminiConfiguration') }}</div>
              <q-input
                v-model="internalModels.gemini_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />
              <!-- Model Selection Button -->
              <div class="model-select-btn" @click="showModelSelector = true">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('chatModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.gemini_chat_model) }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>

            <!-- OpenAI Chat Configuration -->
            <template v-if="providerId === 'openai'">
              <div class="text-subtitle2 q-mb-sm">{{ $t('openaiConfiguration') }}</div>
              <q-input
                v-model="internalModels.openai_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />
              <!-- Model Selection Button -->
              <div class="model-select-btn" @click="showModelSelector = true">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('chatModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.openai_chat_model) }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>

            <!-- Mistral Chat Configuration -->
            <template v-if="providerId === 'mistral'">
              <div class="text-subtitle2 q-mb-sm">{{ $t('mistralConfiguration') }}</div>
              <q-input
                v-model="internalModels.mistral_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />
              <!-- Model Selection Button -->
              <div class="model-select-btn" @click="showModelSelector = true">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('chatModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.mistral_chat_model) }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>

            <!-- Ollama Chat Configuration -->
            <template v-if="providerId === 'ollama'">
              <div class="text-subtitle2 q-mb-sm">{{ $t('ollamaConfiguration') }}</div>
              <q-input
                v-model="internalModels.ollama_base_url"
                :label="$t('baseUrl')"
                outlined
                dense
                :hint="$t('baseUrlHint')"
              />
              <q-input
                v-model="internalModels.ollama_chat_model"
                :label="$t('chatModel')"
                outlined
                dense
              />
            </template>

            <q-separator class="q-my-sm" />

            <div class="text-subtitle2">{{ $t('parameters') }}</div>
            <div class="row q-col-gutter-md">
              <div class="col-6">
                <q-input
                  v-model="internalModels.ai_temperature"
                  :label="$t('temperature')"
                  outlined
                  dense
                  type="number"
                  step="0.1"
                />
              </div>
              <div class="col-6">
                <q-input
                  v-model="internalModels.ai_top_k"
                  :label="$t('topK')"
                  outlined
                  dense
                  type="number"
                />
              </div>
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="bg-secondary text-primary">
          <q-btn flat :label="$t('cancel')" v-close-popup color="grey-7" />
          <q-btn flat :label="$t('save')" type="submit" color="accent" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>

  <!-- Model Selector Dialog -->
  <ModelSelectorDialog
    v-model:is-open="showModelSelector"
    :provider-name="providerName"
    :models="supportedModels"
    :current-model-id="currentModelId"
    @select="handleModelSelect"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, type PropType } from 'vue';
import ModelSelectorDialog from './ModelSelectorDialog.vue';
import type { ModelInfo } from 'src/models/ProviderOption';

const props = defineProps({
  providerId: {
    type: String,
    required: true,
  },
  providerName: {
    type: String,
    default: '',
  },
  models: {
    type: Object as PropType<Record<string, string>>,
    default: () => ({}),
  },
  supportedModels: {
    type: Array as PropType<ModelInfo[]>,
    default: () => [],
  },
});

const emit = defineEmits(['update:isOpen', 'save']);
const isOpen = defineModel<boolean>('isOpen', { default: false });
const showModelSelector = ref(false);

// Local copy of key models to edit
const internalModels = ref<Record<string, string>>({});

watch(
  () => props.models,
  (newVal) => {
    internalModels.value = { ...newVal };
  },
  { immediate: true, deep: true },
);

// Model key for the current provider
const modelKey = computed(() => {
  const map: Record<string, string> = {
    gemini: 'gemini_chat_model',
    openai: 'openai_chat_model',
    mistral: 'mistral_chat_model',
  };
  return map[props.providerId] || '';
});

const currentModelId = computed(() => {
  return internalModels.value[modelKey.value] || '';
});

function getModelDisplayName(modelId: string | undefined): string {
  if (!modelId) return '—';
  const found = props.supportedModels.find((m) => m.id === modelId);
  return found ? found.name : modelId;
}

function handleModelSelect(modelId: string) {
  if (modelKey.value) {
    internalModels.value[modelKey.value] = modelId;
  }
}

function handleSave() {
  emit('save', internalModels.value);
  isOpen.value = false;
}
</script>

<style scoped>
.model-select-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-select-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.18);
}

.model-select-inner {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-select-label {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}

.model-select-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

/* Light mode */
.body--light .model-select-btn {
  background: rgba(0, 0, 0, 0.03);
  border-color: rgba(0, 0, 0, 0.12);
}

.body--light .model-select-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  border-color: rgba(0, 0, 0, 0.2);
}

.body--light .model-select-label {
  color: rgba(0, 0, 0, 0.5);
}

.body--light .model-select-value {
  color: rgba(0, 0, 0, 0.85);
}
</style>
