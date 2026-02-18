<template>
  <q-page class="bg-primary q-pa-lg">
    <q-form no-error-focus>
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

        <div v-else class="full-width q-mb-xl">
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
              <q-tab name="rerank" :label="$t('rerankEngine')" />
              <q-tab name="chat" :label="$t('chatEngine')" />
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
                    <ProviderSelection
                      v-model="models.embedding_provider"
                      :providers="embeddingProviderOptions"
                      show-config-button
                      :config-label="$t('configure')"
                      :config-tooltip="$t('configureProvider')"
                      :selectable="false"
                      :compact="true"
                      grid-cols="col-12 col-sm-6 col-md-3"
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

            <!-- Rerank Engine Tab -->
            <q-tab-panel name="rerank" class="q-px-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <!-- Rerank Provider Selection -->
                  <div class="q-mb-md">
                    <ProviderSelection
                      v-model="models.rerank_provider"
                      :providers="rerankProviderOptions"
                      show-config-button
                      :config-label="$t('configure')"
                      :config-tooltip="$t('configureProvider')"
                      :selectable="false"
                      :compact="true"
                      grid-cols="col-12 col-sm-6 col-md-3"
                      @configure="openRerankConfig"
                    />
                  </div>

                  <!-- Rerank Configuration Dialog -->
                  <RerankConfigurationDialog
                    v-model:isOpen="showRerankConfig"
                    :provider-id="configRerankProviderId"
                    :provider-name="configRerankProviderName"
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
                  <!-- Chat Provider Selection -->
                  <div class="q-mb-md">
                    <ProviderSelection
                      v-model="models.gen_ai_provider"
                      :providers="chatProviderOptions"
                      show-config-button
                      :config-label="$t('configure')"
                      :config-tooltip="$t('configureProvider')"
                      :selectable="false"
                      :compact="true"
                      grid-cols="col-12 col-sm-6 col-md-3"
                      @configure="openChatConfig"
                    />
                  </div>

                  <!-- Chat Configuration Dialog -->
                  <ChatConfigurationDialog
                    v-model:isOpen="showChatConfig"
                    :provider-id="configChatProviderId"
                    :provider-name="configChatProviderName"
                    :models="models"
                    :supported-models="chatSupportedModels"
                    @save="handleConfigSave"
                  />
                </div>
              </div>
            </q-tab-panel>
          </q-tab-panels>
        </div>
      </div>
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
import ProviderSelection from 'src/components/common/ProviderSelection.vue';
import EmbeddingConfigurationDialog from 'src/components/dialogs/EmbeddingConfigurationDialog.vue';
import ChatConfigurationDialog from 'src/components/dialogs/ChatConfigurationDialog.vue';
import RerankConfigurationDialog from 'src/components/dialogs/RerankConfigurationDialog.vue';

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
const tab = ref('general');

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

  // Rerank Settings
  rerank_provider: 'cohere',
  cohere_api_key: '',
  local_rerank_model: 'BAAI/bge-reranker-base',

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

const showChatConfig = ref(false);
const configChatProviderId = ref('');
const configChatProviderName = computed(() => {
  const provider = chatProviderOptions.value.find((p) => p.id === configChatProviderId.value);
  return provider ? provider.name : '';
});
const chatSupportedModels = computed(() => {
  const provider = chatProviderOptions.value.find((p) => p.id === configChatProviderId.value);
  return provider?.supported_models || [];
});

const showRerankConfig = ref(false);
const configRerankProviderId = ref('');
const configRerankProviderName = computed(() => {
  const provider = rerankProviderOptions.value.find((p) => p.id === configRerankProviderId.value);
  return provider ? provider.name : '';
});

// --- COMPUTED ---

const languageOptions = computed(() => [
  {
    label: t('langEnglish'),
    value: 'en-US',
    icon: 'language',
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
const { embeddingProviderOptions, chatProviderOptions, rerankProviderOptions } =
  useAiProviders(models);

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
  } finally {
    loading.value = false;
  }
}

// Replaced global save with specific save function
async function saveSpecificSettings(updatedSettings: Record<string, string>) {
  if (!authStore.isAdmin) return;
  try {
    const updates = [];

    for (const [key, value] of Object.entries(updatedSettings)) {
      const original = originalSettings.find((s) => s.key === key);

      // Determine group/secret if new, or use existing metadata
      let group = 'general';
      let isSecret = false;

      if (original) {
        group = original.group;
        isSecret = original.is_secret;
        // Don't update secrets if value is masked and hasn't changed
        if (isSecret && value === '********') {
          continue;
        }
      } else {
        // Infer for new settings
        isSecret = key.includes('api_key');
        group = key.startsWith('ai') || key.includes('embedding') ? 'ai' : 'general';
      }

      updates.push({
        key,
        value,
        group,
        is_secret: isSecret,
      });
    }

    if (updates.length > 0) {
      await settingsService.updateBatch(updates);
      // We don't notify for every auto-save to avoid spamming, unless it's a manual action
      // But for dialog saves, we might want to.
      // For now, let's just save silently for auto-save, and maybe notify for dialogs if passed a flag?
      // Simpler: just save.

      // Update original settings to reflect new state to avoid redundant saves
      updates.forEach((update) => {
        const index = originalSettings.findIndex((s) => s.key === update.key);
        if (index !== -1 && originalSettings[index]) {
          originalSettings[index].value = update.value;
        } else {
          originalSettings.push(update as Setting);
        }
      });
    }
  } catch (e) {
    console.error('Failed to save settings', e);
  }
}

function openEmbeddingConfig(providerId: string) {
  configProviderId.value = providerId;
  // models.embedding_provider = providerId; // REMOVED: User request to not auto-select
  showEmbeddingConfig.value = true;
}

function openChatConfig(providerId: string) {
  configChatProviderId.value = providerId;
  // models.gen_ai_provider = providerId; // REMOVED: User request to not auto-select
  showChatConfig.value = true;
}

async function handleConfigSave(updatedModels: Record<string, string>) {
  // Merge updates back into main models
  Object.assign(models, updatedModels);

  // Persist immediately
  await saveSpecificSettings(updatedModels);
  notifySuccess(t('settingsSaved'));
  showEmbeddingConfig.value = false;
  showChatConfig.value = false;
  showRerankConfig.value = false;
}

function openRerankConfig(providerId: string) {
  configRerankProviderId.value = providerId;
  // models.rerank_provider = providerId; // REMOVED: User request to not auto-select
  showRerankConfig.value = true;
}

// Auto-save watchers for General Settings using watch
watch(
  () => models.ui_dark_mode,
  (newVal) => {
    if (newVal) {
      void saveSpecificSettings({ ui_dark_mode: newVal });
    }
  },
);

watch(
  () => models.app_language,
  (newVal) => {
    if (newVal) {
      void saveSpecificSettings({ app_language: newVal });
    }
  },
);
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
