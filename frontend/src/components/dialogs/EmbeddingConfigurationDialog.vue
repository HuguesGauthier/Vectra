<template>
  <q-dialog v-model="isOpen">
    <q-card class="bg-primary" style="min-width: 500px">
      <q-card-section class="row items-center q-pb-none bg-secondary">
        <div class="text-h6">{{ providerName }} Configuration</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="q-pt-md">
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
            <q-input
              v-model="internalModels.gemini_embedding_model"
              :label="$t('modelName')"
              outlined
              dense
              :hint="$t('modelNameHint')"
            >
              <template v-slot:append>
                <q-icon name="warning" class="cursor-pointer text-warning">
                  <q-tooltip class="text-body2">{{ $t('modelDeprecationWarning') }}</q-tooltip>
                </q-icon>
              </template>
            </q-input>
            <q-input
              v-model="internalModels.gemini_transcription_model"
              :label="$t('transcriptionModel')"
              outlined
              dense
              :hint="$t('transcriptionModelHint')"
            />
            <q-input
              v-model="internalModels.gemini_extraction_model"
              label="Extraction Model (Ingestion)"
              outlined
              dense
              hint="ex. gemini-2.0-flash"
            />
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
            <q-input
              v-model="internalModels.openai_embedding_model"
              :label="$t('modelName')"
              outlined
              dense
              hint="ex. text-embedding-3-small"
            >
              <template v-slot:append>
                <q-icon name="warning" class="cursor-pointer text-warning">
                  <q-tooltip class="text-body2">{{ $t('modelDeprecationWarning') }}</q-tooltip>
                </q-icon>
              </template>
            </q-input>
          </template>

          <!-- Local Configuration -->
          <template v-if="providerId === 'local'">
            <q-input
              v-model="internalModels.local_embedding_model"
              :label="$t('modelName')"
              outlined
              dense
              hint="ex. nomic-embed-text"
            />

            <div class="text-subtitle2 q-mt-md">
              {{ $t('smartExtractionTitle') }} (Ollama/Mistral)
            </div>
            <q-input
              v-model="internalModels.local_extraction_model"
              label="Extraction Model"
              outlined
              dense
              hint="ex. mistral"
            />
            <q-input
              v-model="internalModels.local_extraction_url"
              label="Ollama Base URL"
              outlined
              dense
              hint="ex. http://localhost:11434"
            />
          </template>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="bg-secondary text-primary">
        <q-btn flat :label="$t('cancel')" v-close-popup color="grey-7" />
        <q-btn flat :label="$t('save')" color="accent" @click="handleSave" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue';
// import { useI18n } from 'vue-i18n';

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
});

const emit = defineEmits(['update:isOpen', 'save']);
const isOpen = defineModel<boolean>('isOpen', { default: false });
// const { t } = useI18n();

// Local copy of key models to edit
const internalModels = ref<Record<string, string>>({});

watch(
  () => props.models,
  (newVal) => {
    // Deep copy specific fields related to the provider to avoid mutating parent state directly before save
    internalModels.value = { ...newVal };
  },
  { immediate: true, deep: true },
);

function handleSave() {
  emit('save', internalModels.value);
  isOpen.value = false;
}
</script>
