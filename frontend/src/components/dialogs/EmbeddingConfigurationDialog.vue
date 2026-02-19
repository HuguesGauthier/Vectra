<template>
  <q-dialog v-model="isOpen">
    <q-card class="bg-primary" style="min-width: 500px; max-height: 80vh; display: flex; flex-direction: column;">


      <q-card-section class="row items-center q-pb-none bg-secondary">
        <div class="text-h6">{{ providerName }} Configuration</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-form @submit="handleSave" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">

        <div class="dialog-body">
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
            <!-- Gemini Configuration -->
            <template v-if="providerId === 'gemini'">
              <q-input
                v-model="internalModels.gemini_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />

              <!-- Embedding Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('gemini_embedding_model', 'embedding')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('modelName') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.gemini_embedding_model, 'embedding') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Transcription Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('gemini_transcription_model', 'transcription')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('transcriptionModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.gemini_transcription_model, 'transcription') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Extraction Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('gemini_extraction_model', 'extraction')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('smartExtractionTitle') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.gemini_extraction_model, 'extraction') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>

            <!-- OpenAI Configuration -->
            <template v-if="providerId === 'openai'">
              <q-input
                v-model="internalModels.openai_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />
              <!-- Embedding Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('openai_embedding_model', 'embedding')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('modelName') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.openai_embedding_model, 'embedding') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Transcription Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('openai_transcription_model', 'transcription')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('transcriptionModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.openai_transcription_model, 'transcription') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Extraction Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('openai_extraction_model', 'extraction')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('smartExtractionTitle') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.openai_extraction_model, 'extraction') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>

            <!-- Local Configuration -->
            <template v-if="providerId === 'local'">
              <div class="row items-center q-mb-sm">
                <div class="text-subtitle2">{{ $t('embeddingEngine') }}</div>
              </div>
              <!-- Embedding Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('local_embedding_model', 'embedding')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('modelName') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.local_embedding_model, 'embedding') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Extraction Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('local_extraction_model', 'extraction')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('smartExtractionTitle') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.local_extraction_model, 'extraction') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
              <q-input
                v-model="internalModels.local_extraction_url"
                label="Ollama Base URL"
                outlined
                dense
                hint="ex. http://localhost:11434"
              />
            </template>

            <!-- Ollama Configuration -->
            <template v-if="providerId === 'ollama'">
              <div class="text-subtitle2 q-mb-sm">{{ $t('embeddingEngine') }}</div>
              <q-input
                v-model="internalModels.ollama_base_url"
                :label="$t('baseUrl')"
                outlined
                dense
                hint="ex. http://localhost:11434"
              />
              
              <!-- Embedding Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('ollama_embedding_model', 'embedding')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('modelName') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.ollama_embedding_model, 'embedding') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              <!-- Transcription Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('ollama_transcription_model', 'transcription')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('transcriptionModel') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.ollama_transcription_model, 'transcription') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>

              
              <!-- Extraction Model Selection -->
              <div class="model-select-btn" @click="openModelSelector('local_extraction_model', 'extraction')">
                <div class="model-select-inner">
                  <div class="model-select-label">{{ $t('smartExtractionTitle') }}</div>
                  <div class="model-select-value">
                    {{ getModelDisplayName(internalModels.local_extraction_model, 'extraction') }}
                  </div>
                </div>
                <q-icon name="chevron_right" color="grey-5" size="20px" />
              </div>
            </template>
          </div>
          </q-card-section>
        </div>

        <q-card-actions align="right" class="bg-secondary text-primary border-top">
          <q-btn flat :label="$t('cancel')" v-close-popup color="grey-7" />
          <q-btn flat :label="$t('save')" type="submit" color="accent" />
        </q-card-actions>
      </q-form>

    </q-card>
  </q-dialog>

  <ModelSelectorDialog
    v-model:is-open="showModelSelector"
    :provider-name="providerName"
    :models="currentSelectorModels"
    :current-model-id="String(currentModelId ?? '')"
    :context="selectorType"
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
    type: Object as PropType<Record<string, string | number | null | undefined>>,
    default: () => ({}),
  },
  supportedModels: {
    type: Array as PropType<ModelInfo[]>,
    default: () => [],
  },
  supportedTranscriptionModels: {
    type: Array as PropType<ModelInfo[]>,
    default: () => [],
  },
  extractionSupportedModels: {
    type: Array as PropType<ModelInfo[]>,
    default: () => [],
  },
});

const emit = defineEmits(['update:isOpen', 'save']);
const isOpen = defineModel<boolean>('isOpen', { default: false });

// Model Selector State
const showModelSelector = ref(false);
const selectorKey = ref('');
const selectorType = ref<'embedding' | 'transcription' | 'extraction'>('embedding');

// Local copy of key models to edit
const internalModels = ref<Record<string, string | number | null | undefined>>({});

watch(
  () => props.models,
  (newVal) => {
    // Deep copy specific fields related to the provider to avoid mutating parent state directly before save
    internalModels.value = { ...newVal };
  },
  { immediate: true, deep: true },
);

const currentSelectorModels = computed(() => {
  if (selectorType.value === 'transcription') return props.supportedTranscriptionModels;
  if (selectorType.value === 'extraction') return props.extractionSupportedModels;
  return props.supportedModels;
});

const currentModelId = computed(() => {
  return internalModels.value[selectorKey.value] || '';
});

function openModelSelector(key: string, type: 'embedding' | 'transcription' | 'extraction') {
  selectorKey.value = key;
  selectorType.value = type;
  showModelSelector.value = true;
}

function handleModelSelect(modelId: string) {
  if (selectorKey.value) {
    internalModels.value[selectorKey.value] = modelId;
  }
}

function getModelDisplayName(modelId: string | number | null | undefined, type: 'embedding' | 'transcription' | 'extraction'): string {
  if (!modelId) return '—';
  
  let list = props.supportedModels;
  if (type === 'transcription') list = props.supportedTranscriptionModels;
  if (type === 'extraction') list = props.extractionSupportedModels;
  
  const found = list.find((m) => m.id === modelId);
  return found ? found.name : String(modelId ?? '');
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
  margin-bottom: 8px;
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

.border-top {
  border-top: 1px solid var(--q-sixth);
}

.dialog-body {
  overflow-y: auto;
  flex: 1;
}

</style>
