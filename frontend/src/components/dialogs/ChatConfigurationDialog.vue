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
              <q-input
                v-model="internalModels.gemini_chat_model"
                :label="$t('chatModel')"
                outlined
                dense
                :hint="$t('chatModelHintGemini')"
              />
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
              <q-input
                v-model="internalModels.openai_chat_model"
                :label="$t('chatModel')"
                outlined
                dense
                :hint="$t('chatModelHintOpenAI')"
              />
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
              <q-input
                v-model="internalModels.mistral_chat_model"
                :label="$t('chatModel')"
                outlined
                dense
              />
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
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue';

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
