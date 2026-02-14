<template>
  <q-page class="bg-primary q-pa-lg">
    <q-form @submit="saveSettings" no-error-focus>
      <!-- Hidden username to satisfy browser heuristics for password forms -->
      <input
        type="text"
        name="username"
        autocomplete="username"
        style="display: none; opacity: 0; position: absolute; left: -9999px"
        tabindex="-1"
      />

      <!-- Header -->
      <div class="row items-center justify-between q-pt-md q-pb-md q-pl-none q-mb-md">
        <div>
          <div class="text-h4 text-weight-bold">{{ $t('settings') }}</div>
          <div class="text-subtitle1 q-pt-xs">
            {{ $t('manageAppConfiguration') }}
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div>
        <!-- Loading State -->
        <div v-if="loading" class="row justify-center q-pa-xl">
          <q-spinner size="40px" color="accent" />
        </div>

        <div v-else style="max-width: 800px; margin-bottom: 80px">
          <q-tabs
            v-model="tab"
            dense
            class="modern-tabs"
            active-color="white"
            indicator-color="transparent"
            align="left"
            no-caps
            inline-label
            outside-arrows
            mobile-arrows
          >
            <q-tab name="general" :label="$t('general')" />
            <template v-if="authStore.isAdmin">
              <q-tab name="embedding" :label="$t('embeddingEngine')" />
              <q-tab name="chat" :label="$t('chatEngine')" />
              <q-tab name="system" :label="$t('system')" />
            </template>
          </q-tabs>

          <q-separator class="q-mb-md" />

          <q-tab-panels v-model="tab" animated class="bg-transparent">
            <!-- General Tab -->
            <q-tab-panel name="general" class="q-px-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-card flat bordered class="bg-secondary">
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('interface') }}
                      </div>

                      <!-- Language -->
                      <div class="q-mb-md">
                        <div class="text-caption q-mb-xs">
                          {{ $t('language') }}
                        </div>
                        <CardSelection v-model="models.app_language" :options="languageOptions" />
                      </div>

                      <!-- Dark Mode -->
                      <div>
                        <div class="text-caption q-mb-xs">
                          {{ $t('theme') }}
                        </div>
                        <CardSelection v-model="models.ui_dark_mode" :options="themeOptions" />
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
              </div>
            </q-tab-panel>

            <!-- Vectorization Engine Tab -->
            <q-tab-panel name="embedding" class="q-px-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <!-- Embedding Provider Selection -->
                  <div class="q-mb-md">
                    <EmbeddingSelection
                      v-model="models.embedding_provider"
                      :providers="embeddingProviderOptions"
                      show-config-button
                      :config-label="$t('configure')"
                      :config-tooltip="$t('configureProvider')"
                      :selectable="false"
                      @configure="openEmbeddingConfig"
                    />
                  </div>

                  <!-- Configuration Dialog -->
                  <EmbeddingConfigurationDialog
                    v-model:isOpen="showEmbeddingConfig"
                    :provider-id="configProviderId"
                    :provider-name="configProviderName"
                    :models="models"
                    @save="handleConfigSave"
                  />
                </div>
              </div>
            </q-tab-panel>

            <!-- Chat/Generation Tab -->
            <q-tab-panel name="chat" class="q-px-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-banner v-if="hasChanges" rounded class="bg-warning text-dark q-mb-md">
                    <template v-slot:avatar>
                      <q-icon name="warning" />
                    </template>
                    {{ $t('restartRequiredInfo') }}
                  </q-banner>

                  <q-banner rounded class="bg-info text-white q-mb-md" dense>
                    <template v-slot:avatar>
                      <q-icon name="mdi-chat-processing" />
                    </template>
                    {{ $t('chatModelHint') }}
                  </q-banner>

                  <!-- Chat Provider Selection -->
                  <q-card flat bordered class="bg-secondary q-mb-md">
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('chatProvider') }}
                      </div>
                      <q-select
                        v-model="models.gen_ai_provider"
                        :options="chatProviderOptions"
                        outlined
                        dense
                        color="accent"
                        emit-value
                        map-options
                      />
                    </q-card-section>
                  </q-card>

                  <!-- Gemini Chat Config -->
                  <q-card
                    v-if="models.gen_ai_provider === 'gemini'"
                    flat
                    bordered
                    class="bg-secondary"
                  >
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('geminiConfiguration') }}
                      </div>
                      <q-input
                        v-model="models.gemini_api_key"
                        :label="$t('apiKey')"
                        outlined
                        dense
                        type="password"
                        autocomplete="new-password"
                      />
                      <q-input
                        v-model="models.gemini_chat_model"
                        :label="$t('chatModel')"
                        outlined
                        dense
                        :hint="$t('chatModelHintGemini')"
                      />
                    </q-card-section>
                  </q-card>

                  <!-- OpenAI Chat Config -->
                  <q-card
                    v-if="models.gen_ai_provider === 'openai'"
                    flat
                    bordered
                    class="bg-secondary"
                  >
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('openaiConfiguration') }}
                      </div>
                      <div class="column q-gutter-y-md">
                        <q-input
                          v-model="models.openai_api_key"
                          :label="$t('apiKey')"
                          outlined
                          dense
                          type="password"
                          autocomplete="new-password"
                        />
                        <q-input
                          v-model="models.openai_chat_model"
                          :label="$t('chatModel')"
                          outlined
                          dense
                          :hint="$t('chatModelHintOpenAI')"
                        />
                      </div>
                    </q-card-section>
                  </q-card>

                  <!-- Mistral Chat Config -->
                  <q-card
                    v-if="models.gen_ai_provider === 'mistral'"
                    flat
                    bordered
                    class="bg-secondary"
                  >
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('mistralConfiguration') }}
                      </div>
                      <div class="column q-gutter-y-md">
                        <q-input
                          v-model="models.mistral_api_key"
                          :label="$t('apiKey')"
                          outlined
                          dense
                          type="password"
                          autocomplete="new-password"
                        />
                        <q-input
                          v-model="models.mistral_chat_model"
                          :label="$t('chatModel')"
                          outlined
                          dense
                        />
                      </div>
                    </q-card-section>
                  </q-card>

                  <!-- Ollama Chat Config -->
                  <q-card
                    v-if="models.gen_ai_provider === 'ollama'"
                    flat
                    bordered
                    class="bg-secondary"
                  >
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('ollamaConfiguration') }}
                      </div>
                      <div class="column q-gutter-y-md">
                        <q-input
                          v-model="models.ollama_base_url"
                          :label="$t('baseUrl')"
                          outlined
                          dense
                          :hint="$t('baseUrlHint')"
                        />
                        <q-input
                          v-model="models.ollama_chat_model"
                          :label="$t('chatModel')"
                          outlined
                          dense
                        />
                      </div>
                    </q-card-section>
                  </q-card>

                  <!-- Parameters -->
                  <q-card flat bordered class="bg-secondary q-mt-md">
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('parameters') }}
                      </div>
                      <div class="row q-col-gutter-md">
                        <div class="col-6">
                          <q-input
                            v-model="models.ai_temperature"
                            :label="$t('temperature')"
                            outlined
                            dense
                            type="number"
                            step="0.1"
                          />
                        </div>
                        <div class="col-6">
                          <q-input
                            v-model="models.ai_top_k"
                            :label="$t('topK')"
                            outlined
                            dense
                            type="number"
                          />
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
              </div>
            </q-tab-panel>

            <!-- System Tab -->
            <q-tab-panel name="system" class="q-px-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-card flat bordered class="bg-secondary">
                    <q-card-section>
                      <div class="text-subtitle1 text-weight-bold q-mb-sm">
                        {{ $t('network') }}
                      </div>
                      <q-input
                        v-model="models.system_proxy"
                        :label="$t('httpProxy')"
                        outlined
                        dense
                        placeholder="http://user:pass@host:port"
                        :hint="$t('proxyHint')"
                      />
                    </q-card-section>
                  </q-card>
                </div>
              </div>
            </q-tab-panel>
          </q-tab-panels>
        </div>
      </div>

      <!-- Footer (Fixed at bottom) -->
      <q-page-sticky position="bottom" expand :offset="[0, 0]" style="z-index: 100">
        <div class="full-width bg-secondary q-pa-md border-top row justify-end items-center">
          <q-btn
            color="accent"
            :label="$t('saveChanges')"
            unelevated
            :disable="saving || !authStore.isAdmin"
            type="submit"
            text-color="grey-3"
            no-ripple
            v-if="authStore.isAdmin"
          />
        </div>
      </q-page-sticky>
    </q-form>
  </q-page>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { settingsService } from 'src/services/settingsService';
import { useNotification } from 'src/composables/useNotification';
import { useAiProviders } from 'src/composables/useAiProviders';
import { useAuthStore } from 'src/stores/authStore';
import { useTheme } from 'src/composables/useTheme'; // Added import
import { useQuasar } from 'quasar';
import type { Setting } from 'src/models/Setting';
import CardSelection from 'src/components/common/CardSelection.vue';
import EmbeddingSelection from 'src/components/common/EmbeddingSelection.vue';
import EmbeddingConfigurationDialog from 'src/components/dialogs/EmbeddingConfigurationDialog.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'SettingsPage',
});

const $q = useQuasar();
const { t, locale } = useI18n();
const { notifySuccess } = useNotification();

const authStore = useAuthStore();
const { themePreference, setParams } = useTheme(); // Added usage

// --- STATE ---

const loading = ref(true);
const saving = ref(false);
const tab = ref('general');
const hasChanges = ref(false);

// Local state model
const models = reactive<Record<string, string>>({
  app_language: 'fr',
  ui_dark_mode: themePreference.value, // Initialize with current theme preference

  // Ingestion/Embedding Settings
  embedding_provider: 'gemini',
  gemini_api_key: '',
  gemini_embedding_model: 'models/text-embedding-004',
  gemini_transcription_model: 'gemini-1.5-flash',
  gemini_extraction_model: 'gemini-2.0-flash',
  openai_api_key: '',
  openai_embedding_model: 'text-embedding-3-small',
  local_embedding_url: 'http://localhost:11434',
  local_embedding_model: 'nomic-embed-text',
  local_extraction_model: 'mistral',
  local_extraction_url: 'http://localhost:11434',

  // Chat/Generation Settings
  gen_ai_provider: 'gemini',
  gemini_chat_model: 'gemini-1.5-flash',
  openai_chat_model: 'gpt-4-turbo',
  mistral_api_key: '',
  mistral_chat_model: 'mistral-large-latest',
  ollama_base_url: 'http://localhost:11434',
  ollama_chat_model: 'mistral',
  ollama_embedding_model: 'bge-m3',

  // Shared Parameters
  ai_temperature: '0.2',
  ai_top_k: '5',
  system_proxy: '',
});

// Original raw settings (not reactive)
let originalSettings: Setting[] = [];

// Dialog State
const showEmbeddingConfig = ref(false);
const configProviderId = ref('');
const configProviderName = computed(() => {
  const provider = embeddingProviderOptions.value.find((p) => p.id === configProviderId.value);
  return provider ? provider.name : '';
});

// --- COMPUTED ---

const languageOptions = computed(() => [
  {
    label: t('langEnglish'),
    value: 'en-US',
    icon: 'translate',
    description: 'English',
  },
  {
    label: t('langFrench'),
    value: 'fr',
    icon: 'language',
    description: 'Français',
  },
]);

const themeOptions = computed(() => [
  {
    label: t('themeAuto'),
    value: 'auto',
    icon: 'brightness_auto',
    description: 'Follow system',
  },
  {
    label: t('themeDark'),
    value: 'dark',
    icon: 'dark_mode',
    description: 'Dark mode',
  },
  {
    label: t('themeLight'),
    value: 'light',
    icon: 'light_mode',
    description: 'Light mode',
  },
]);

// Import centralized AI provider options
const { embeddingProviderOptions, chatProviderOptions } = useAiProviders();

// --- WATCHERS ---

// Sync locale when model changes if user wants immediate feedback
watch(
  () => models.app_language,
  (newVal) => {
    if (newVal) {
      locale.value = newVal;
      // Persist to localStorage for boot/refresh
      localStorage.setItem('app_language', newVal);
      // Also update Quasar lang pack if needed
      // Also update Quasar lang pack if needed
      import(/* @vite-ignore */ `quasar/lang/${newVal === 'en-US' ? 'en-US' : newVal}`)
        .then((lang) => {
          $q.lang.set(lang.default);
        })
        .catch(() => {
          // Fallback or ignore if pack not found
        });
    }
  },
);

// Watch for theme changes from the UI and apply them immediately
watch(
  () => models.ui_dark_mode,
  (newVal) => {
    if (newVal) {
      void setParams(newVal as 'auto' | 'dark' | 'light');
    }
  },
);

// --- FUNCTIONS ---

onMounted(() => {
  if (authStore.isAdmin) {
    void loadSettings();
  } else {
    // For non-admin, just stop loading, we rely on defaults/local state
    loading.value = false;
  }
});

// onUnmounted removed as no listeners needed

// handleWsDebug removed
// clearLogs removed

async function loadSettings() {
  try {
    loading.value = true;
    const settings = await settingsService.getAll();
    originalSettings = settings;

    // Map to models
    settings.forEach((s) => {
      if (s.key in models) {
        models[s.key] = s.value;
      }
    });

    // FORCE GEMINI - REMOVED
    // models.embedding_provider = 'gemini';
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  if (!authStore.isAdmin) return; // Prevent saving for non-admins
  try {
    saving.value = true;
    const updates = [];

    // Determine what changed
    for (const [key, value] of Object.entries(models)) {
      const original = originalSettings.find((s) => s.key === key);

      // If no original, or value changed
      // Special check for secrets: if value is ********, don't update unless changed
      if (original) {
        if (original.is_secret && value === '********') {
          continue; // No change
        }
        if (original.value !== value) {
          updates.push({
            key,
            value,
            group: original.group,
            is_secret: original.is_secret,
          });
        }
      } else {
        // New setting (shouldn't happen often if seeded)
        // Infer group/secret
        const isSecret = key.includes('api_key');
        const group = key.startsWith('ai') || key.includes('embedding') ? 'ai' : 'general';
        updates.push({
          key,
          value,
          group,
          is_secret: isSecret,
        });
      }
    }

    if (updates.length > 0) {
      await settingsService.updateBatch(updates);
      notifySuccess(t('settingsSaved'));
      await loadSettings(); // Reload to get masks
      hasChanges.value = false;
    } else {
      notifySuccess(t('noChanges'));
    }
  } finally {
    saving.value = false;
  }
}

function openEmbeddingConfig(providerId: string) {
  configProviderId.value = providerId;
  // If clicking configure on a provider that isn't selected, select it?
  // Probably yes for better UX, or keep it independent.
  // Let's select it for now.
  models.embedding_provider = providerId;
  showEmbeddingConfig.value = true;
}

function handleConfigSave(updatedModels: Record<string, string>) {
  // Merge updates back into main models
  Object.assign(models, updatedModels);
  hasChanges.value = true;
}
</script>
<style scoped>
/* Modern Tabs Styling */
.modern-tabs {
  background: transparent;
}

:deep(.modern-tabs .q-tab) {
  border-radius: 8px;
  margin-right: 8px;
  min-height: 28px;
  transition: all 0.3s ease;
  opacity: 0.7;
  border: 1px solid transparent;
  color: var(--q-text-sub);
}

:deep(.modern-tabs .q-tab:hover) {
  opacity: 1;
  background: rgba(255, 255, 255, 0.05);
  color: var(--q-text-main);
}

:deep(.modern-tabs .q-tab--active) {
  opacity: 1;
  background: var(--q-accent);
  color: white !important;
  border-color: var(--q-accent);
  box-shadow: 0 4px 12px rgba(var(--q-accent-rgb), 0.3);
}

/* Hide the default ripple for a cleaner feel */
:deep(.modern-tabs .q-focus-helper) {
  display: none;
}
</style>
