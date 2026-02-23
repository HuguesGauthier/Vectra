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


      <!-- Main Content -->
      <div class="row q-col-gutter-lg">
        <!-- Sidebar Navigation -->
        <div class="col-12 col-md-3">
          <div class="settings-sidebar">
            <div class="sidebar-header q-mb-lg q-px-md">
              <div class="text-h5 text-weight-bolder">{{ $t('settings') }}</div>
              <div class="text-caption ">{{ $t('manageAppConfiguration') }}</div>
            </div>

            <div class="nav-list">
              <div
                v-for="item in navItems"
                :key="item.name"
                class="nav-item"
                :class="{ active: tab === item.name }"
                @click="tab = item.name"
              >
                <div class="active-glow" v-if="tab === item.name"></div>
                <q-icon :name="item.icon" size="20px" class="q-mr-md nav-icon" />
                <div class="nav-label text-weight-bold">{{ item.label }}</div>
                <q-icon name="chevron_right" size="xs" class="chevron-indicator" />
              </div>
            </div>
          </div>
        </div>

        <!-- Tab Panels (Content Area) -->
        <div class="col-12 col-md-9">
          <!-- Loading State -->
          <div v-if="loading" class="row justify-center q-pa-xl">
            <q-spinner size="40px" color="accent" />
          </div>

          <q-tab-panels v-else v-model="tab" animated transition-prev="fade" transition-next="fade" class="bg-transparent overflow-visible">
            <!-- General Tab -->
            <q-tab-panel name="general" class="q-pa-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-card flat class="settings-card">
                    <q-card-section>
                      <div class="section-title q-mb-lg">
                        <q-icon name="display_settings" size="sm" color="accent" class="q-mr-sm" />
                        {{ $t('interface') }}
                      </div>

                      <!-- Language -->
                      <div class="q-mb-xl">
                        <div class="text-subtitle2 q-mb-sm text-grey-4">
                          {{ $t('language') }}
                        </div>
                        <CardSelection v-model="models.app_language" :options="languageOptions" />
                      </div>

                      <!-- Dark Mode -->
                      <div>
                        <div class="text-subtitle2 q-mb-sm text-grey-4">
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
            <q-tab-panel name="embedding" class="q-pa-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <div class="section-title q-mb-md">
                    <q-icon name="psychology" size="sm" color="accent" class="q-mr-sm" />
                    {{ $t('embeddingEngine') }}
                  </div>
                  <!-- Embedding Provider Selection -->
                  <div class="q-mb-md">
                    <AiProviderGrid
                      :providers="embeddingProviderOptions"
                      show-config
                      force-enabled
                      grid-cols="col-12 col-sm-6 col-lg-4"
                      @configure="openEmbeddingConfig"
                    />
                  </div>

                  <!-- Configuration Dialog -->
                  <EmbeddingConfigurationDialog
                    v-model:isOpen="showEmbeddingConfig"
                    :provider-id="configProviderId"
                    :provider-name="configProviderName"
                    :models="models"
                    :supported-models="embeddingSupportedModels"
                    :supported-transcription-models="transcriptionSupportedModels"
                    :extraction-supported-models="extractionSupportedModels"
                    @save="handleConfigSave"
                  />
                </div>
              </div>
            </q-tab-panel>

            <!-- Rerank Engine Tab -->
            <q-tab-panel name="rerank" class="q-pa-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <div class="section-title q-mb-md">
                    <q-icon name="sort" size="sm" color="accent" class="q-mr-sm" />
                    {{ $t('rerankEngine') }}
                  </div>
                  <!-- Rerank Provider Selection -->
                  <div class="q-mb-md">
                    <AiProviderGrid
                      :providers="rerankProviderOptions"
                      show-config
                      force-enabled
                      grid-cols="col-12 col-sm-6 col-lg-4"
                      @configure="openRerankConfig"
                    />
                  </div>

                  <!-- Rerank Configuration Dialog -->
                  <RerankConfigurationDialog
                    v-model:isOpen="showRerankConfig"
                    :provider-id="configRerankProviderId"
                    :provider-name="configRerankProviderName"
                    :models="models"
                    :supported-models="rerankSupportedModels"
                    @save="handleConfigSave"
                  />
                </div>
              </div>
            </q-tab-panel>

            <!-- Chat/Generation Tab -->
            <q-tab-panel name="chat" class="q-pa-none">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <div class="section-title q-mb-md">
                    <q-icon name="forum" size="sm" color="accent" class="q-mr-sm" />
                    {{ $t('chatEngine') }}
                  </div>
                  <!-- Chat Provider Selection -->
                  <div class="q-mb-md">
                    <AiProviderGrid
                      :providers="chatProviderOptions"
                      show-config
                      force-enabled
                      grid-cols="col-12 col-sm-6 col-lg-4"
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
import AiProviderGrid from 'src/components/common/AiProviderGrid.vue';
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

// Navigation items for the sidebar
const navItems = computed(() => {
  const items = [
    { name: 'general', label: t('general'), icon: 'tune' }
  ];
  
  if (authStore.isAdmin) {
    items.push(
      { name: 'embedding', label: t('embeddingEngine'), icon: 'psychology' },
      { name: 'rerank', label: t('rerankEngine'), icon: 'sort' },
      { name: 'chat', label: t('chatEngine'), icon: 'forum' }
    );
  }
  
  return items;
});

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
  openai_transcription_model: 'whisper-1',
  openai_extraction_model: 'gpt-4o-mini',
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
  anthropic_api_key: '',
  anthropic_chat_model: 'claude-3-7-sonnet-latest',
  ollama_base_url: 'http://localhost:11434',
  ollama_chat_model: 'mistral',
  ollama_embedding_model: 'bge-m3',
  ollama_transcription_model: 'whisper',

  // Rerank Settings
  rerank_provider: 'cohere',
  cohere_api_key: '',
  local_rerank_model: 'BAAI/bge-reranker-base',

  // Shared Parameters
  ai_temperature: '0.2',
  ai_top_k: '5',

  // Provider Specific Parameters
  gemini_temperature: '',
  gemini_top_k: '',
  openai_temperature: '',
  openai_top_k: '',
  mistral_temperature: '',
  mistral_top_k: '',
  anthropic_temperature: '',
  anthropic_top_k: '',
  ollama_temperature: '',
  ollama_top_k: '',

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

const embeddingSupportedModels = computed(() => {
  const provider = embeddingProviderOptions.value.find((p) => p.id === configProviderId.value);
  return provider?.supported_models || [];
});

const transcriptionSupportedModels = computed(() => {
  const provider = embeddingProviderOptions.value.find((p) => p.id === configProviderId.value);
  return provider?.supported_transcription_models || [];
});

const extractionSupportedModels = computed(() => {
  // Find the chat provider that matches the current embedding provider ID
  const chatProvider = chatProviderOptions.value.find((p) => p.id === configProviderId.value);
  return chatProvider?.supported_models || [];
});

const showRerankConfig = ref(false);
const configRerankProviderId = ref('');
const configRerankProviderName = computed(() => {
  const provider = rerankProviderOptions.value.find((p) => p.id === configRerankProviderId.value);
  return provider ? provider.name : '';
});

const rerankSupportedModels = computed(() => {
  const provider = rerankProviderOptions.value.find((p) => p.id === configRerankProviderId.value);
  return provider?.supported_models || [];
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
        value: String(value ?? ''),
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
.settings-sidebar {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  padding: 24px 0;
  position: sticky;
  top: 24px;
}

.sidebar-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 20px;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 14px 18px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  color: var(--q-text-sub);
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--q-text-main);
}

.nav-item.active {
  background: var(--q-secondary);
}

.nav-icon {
  transition: transform 0.3s ease;
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
}

.nav-item.active .nav-icon {
  color: var(--q-accent);
}

.active-glow {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 0 4px 4px 0;
}

.chevron-indicator {
  margin-left: auto;
  opacity: 0;
  transition: all 0.3s ease;
  transform: translateX(-10px);
}

.nav-item.active .chevron-indicator {
  opacity: 1;
  transform: translateX(0);
}

.settings-card {
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(5px);
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  padding: 12px;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
  color: var(--q-text-main);
}

.overflow-visible {
  overflow: visible !important;
}

/* Responsive adjustments */
@media (max-width: 1023px) {
  .settings-sidebar {
    position: static;
    margin-bottom: 24px;
  }
  
  .nav-list {
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 8px;
  }
  
  .nav-item {
    white-space: nowrap;
  }
  
  .active-glow {
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;
    width: auto;
    height: 3px;
    border-radius: 4px 4px 0 0;
  }
}
</style>
