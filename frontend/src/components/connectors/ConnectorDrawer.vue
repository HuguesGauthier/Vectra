<template>
  <q-dialog v-model="isOpen" maximized position="right">
    <q-card class="bg-primary text-grey-5 column full-height" style="min-width: 50vw">
      <!-- Header -->
      <div class="q-pa-md bg-secondary border-bottom row items-center justify-between">
        <div class="text-h6">
          {{ props.title || $t('editConnector', { type: '' }).replace('  ', ' ') }}
        </div>
        <q-btn flat round dense icon="close" @click="handleClose" />
      </div>

      <!-- Tabs Navigation -->
      <div class="q-px-md q-pt-md bg-primary">
        <q-tabs
          v-model="activeTab"
          dense
          align="justify"
          class="modern-tabs"
          active-color="white"
          indicator-color="transparent"
          no-caps
          outside-arrows
          mobile-arrows
        >
          <q-tab name="config" icon="settings" :label="$t('configuration')" />
          <q-tab name="vectorization" icon="psychology" :label="$t('embeddingEngine')" />
          <q-tab name="schedule" icon="event" :label="$t('schedule')" />
          <q-tab name="access" icon="lock" :label="$t('access')" />
        </q-tabs>
      </div>

      <!-- Tab Panels -->
      <q-form ref="formRef" @submit.prevent="handleSave" class="col column">
        <q-tab-panels v-model="activeTab" animated class="col scroll bg-primary q-mt-md">
          <!-- Tab 1: Configuration with Vertical Sub-tabs -->
          <q-tab-panel name="config" class="q-pa-none">
            <div class="row full-height">
              <!-- Vertical Sub-tabs -->
              <q-tabs
                v-model="configSubTab"
                vertical
                class="text-grey-5 bg-secondary"
                active-color="accent"
                indicator-color="accent"
                style="min-width: 200px"
              >
                <q-tab name="general" icon="info" :label="$t('generalInfo')" />
                <q-tab name="connection" icon="dns" :label="$t('connectionDetails')" />
              </q-tabs>

              <!-- Sub-tab Panels -->
              <q-tab-panels
                v-model="configSubTab"
                animated
                vertical
                transition-prev="slide-down"
                transition-next="slide-up"
                class="col bg-primary q-pa-md"
              >
                <!-- General Information -->
                <q-tab-panel name="general">
                  <ConfigurationGeneralFields v-model="generalConfig" />
                </q-tab-panel>

                <!-- Connection Details -->
                <q-tab-panel name="connection">
                  <component
                    :is="typeConfigComponent"
                    v-if="typeConfigComponent"
                    v-model="typeSpecificConfig"
                  />
                </q-tab-panel>
              </q-tab-panels>
            </div>
          </q-tab-panel>

          <!-- Tab 2: Vectorization -->
          <q-tab-panel name="vectorization">
            <div class="q-gutter-md q-pl-md">
              <div class="text-subtitle2 text-grey-5 q-mb-xs">
                {{ $t('selectVectorizationEngineDesc') }}
              </div>

              <ProviderSelection
                v-model="indexationConfig.ai_provider"
                :providers="embeddingProviderOptions"
                :disable-config="isEditing"
                class="q-mb-md"
              />

              <!-- Advanced Settings Button -->
              <div class="row justify-end q-mt-sm">
                <q-btn
                  flat
                  color="accent"
                  icon="tune"
                  :label="$t('advancedSettings')"
                  size="sm"
                  @click="showAdvancedSettings = true"
                />
              </div>

              <AdvancedIndexingSettings
                v-model:isOpen="showAdvancedSettings"
                :chunk-size="data?.chunk_size ?? 300"
                :chunk-overlap="data?.chunk_overlap ?? 30"
                @update="updateChunkingConfig"
              />

              <!-- Smart Extraction -->
              <SmartExtractionConfig v-model="indexationConfig.use_smart_extraction" />

              <!-- Banners Container -->
              <div style="max-width: 800px; margin: 50px auto; width: 100%">
                <!-- Warning for Local Provider -->
                <q-banner
                  v-if="indexationConfig.ai_provider === 'local'"
                  rounded
                  class="bg-warning text-dark"
                >
                  <template v-slot:avatar>
                    <q-icon name="warning" color="dark" />
                  </template>
                  {{ $t('localProviderWarning') }}
                </q-banner>
              </div>
            </div>
          </q-tab-panel>

          <!-- Tab 3: Schedule -->
          <q-tab-panel name="schedule">
            <div class="q-gutter-md">
              <div class="text-subtitle1 row justify-center q-mb-xs">
                {{ $t('syncScheduleDesc') }}
              </div>

              <ScheduleOptions
                v-model="indexationConfig.schedule_cron"
                :connector-type="props.connectorType || data?.connector_type"
              />
            </div>
          </q-tab-panel>

          <!-- Tab 4: Access -->
          <q-tab-panel name="access">
            <AccessFields v-model="aclConfig" />
          </q-tab-panel>
        </q-tab-panels>
      </q-form>

      <!-- Footer -->
      <div class="q-pa-md border-top bg-secondary row justify-end q-gutter-sm">
        <q-btn flat :label="$t('cancel')" color="grey-7" @click="handleClose" />
        <q-btn
          unelevated
          :label="$t('save')"
          color="accent"
          text-color="grey-3"
          @click="submitForm"
          :loading="props.loading"
        />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, type Component, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { Connector } from 'src/models/Connector';
import { ScheduleType } from 'src/models/enums';
import { useDialog } from 'src/composables/useDialog';
import { useAiProviders } from 'src/composables/useAiProviders';
import ProviderSelection from 'src/components/common/ProviderSelection.vue';

// Field components
import ConfigurationGeneralFields from './fields/ConfigurationGeneralFields.vue';
import AccessFields from './fields/AccessFields.vue';
import FolderConfigFields from './fields/FolderConfigFields.vue';
import SqlConfigFields from './fields/SqlConfigFields.vue';
import FileConfigFields from './fields/FileConfigFields.vue';
import AdvancedIndexingSettings from './dialogs/AdvancedIndexingSettings.vue';
import SmartExtractionConfig from './fields/SmartExtractionConfig.vue';
import ScheduleOptions from './ScheduleOptions.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'ConnectorDrawer',
});

const model = defineModel<boolean>({ required: true });
const data = defineModel<Connector | undefined>('data');

const props = defineProps<{
  connectorType: string;
  title?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'save', payload: { type: string; data: Connector }): void;
}>();

// --- STATE ---
const { t } = useI18n();
const { confirm } = useDialog();
const { embeddingProviderOptions } = useAiProviders();

const formRef = ref();
const activeTab = ref('config');
const configSubTab = ref('general'); // Sub-tab state for Configuration tab
const initialDataStr = ref('');
const showAdvancedSettings = ref(false);

// Type definitions for connector-specific configurations
type FolderConfig = { path: string; recursive?: boolean };
type SqlConfig = {
  host: string;
  port: number;
  database: string;
  schema: string;
  user: string;
  password: string;
};
type FileConfig = Record<string, never>; // Empty object
type ConnectorSpecificConfig = FolderConfig | SqlConfig | FileConfig;

interface IndexationConfig {
  ai_provider: string;
  schedule_cron?: string | undefined;
  recursive?: boolean;
  use_smart_extraction: boolean;
}

// Configuration state
const generalConfig = ref<{ name: string; description: string }>({
  name: '',
  description: '',
});

const typeSpecificConfig = ref<ConnectorSpecificConfig>({});

const indexationConfig = ref<IndexationConfig>({
  ai_provider: 'gemini',
  schedule_cron: undefined,
  recursive: false,
  use_smart_extraction: false,
});

const aclConfig = ref<string[] | string>([]);

// --- COMPUTED ---
const isEditing = computed(() => !!data.value?.id);

const isOpen = computed({
  get: () => model.value,
  set: (val) => {
    if (!val) handleClose();
    else model.value = val;
  },
});

// Dynamic component mapping
const typeConfigComponents: Record<string, Component> = {
  local_folder: FolderConfigFields,
  folder: FolderConfigFields, // Legacy
  sql: SqlConfigFields,
  local_file: FileConfigFields,
  file: FileConfigFields, // Legacy
};

const typeConfigComponent = computed(
  () =>
    typeConfigComponents[props.connectorType] ||
    typeConfigComponents[data.value?.connector_type as string],
);

// --- WATCHERS ---

// Populate fields when data changes
watch(
  data,
  (newData) => {
    if (newData) {
      // General config
      generalConfig.value = {
        name: newData.name || '',
        description: newData.description || '',
      };

      indexationConfig.value = {
        ai_provider: newData.configuration?.ai_provider || 'gemini',
        schedule_cron: newData.schedule_cron,
        recursive: newData.configuration?.recursive,
        use_smart_extraction: newData.configuration?.indexing_config?.use_smart_extraction || false,
      };

      // ACL config
      aclConfig.value = newData.configuration?.connector_acl || [];

      // Type-specific config
      typeSpecificConfig.value = extractTypeSpecificConfig(newData);

      // Save initial state
      initialDataStr.value = JSON.stringify({
        general: generalConfig.value,
        indexation: indexationConfig.value,
        acl: aclConfig.value,
        typeSpecific: typeSpecificConfig.value,
      });
    }
  },
  { immediate: true },
);

// --- FUNCTIONS ---

function updateChunkingConfig(payload: { chunkSize: number; chunkOverlap: number }) {
  if (!data.value) return;
  data.value.chunk_size = payload.chunkSize;
  data.value.chunk_overlap = payload.chunkOverlap;
}

function extractTypeSpecificConfig(connector: Connector): ConnectorSpecificConfig {
  const config = connector.configuration || {};

  // Ideally handle generic type if props.connectorType is not set (e.g. valid when editing)
  const type = props.connectorType || connector.connector_type;

  switch (type) {
    case 'local_folder':
    case 'folder': // Legacy support
      return {
        path: config.path || '',
        recursive: config.recursive,
      };
    case 'sql':
      return {
        host: config.host || '',
        port: config.port || 5432,
        database: config.database || '',
        schema: config.schema || 'vectra',
        user: config.user || '',
        password: config.password || '',
      };
    case 'local_file':
    case 'file': // Legacy support
    default:
      return {};
  }
}

function handleClose() {
  const currentDataStr = JSON.stringify({
    general: generalConfig.value,
    indexation: indexationConfig.value,
    acl: aclConfig.value,
    typeSpecific: typeSpecificConfig.value,
  });

  if (currentDataStr !== initialDataStr.value) {
    confirm({
      title: t('unsavedChanges'),
      message: t('unsavedChangesMessage'),
      confirmLabel: t('discard'),
      confirmColor: 'negative',
      cancelLabel: t('keepEditing'),
      onConfirm: () => {
        model.value = false;
        activeTab.value = 'config'; // Reset to first tab
      },
      onCancel: () => {},
    });
    return;
  }
  model.value = false;
  activeTab.value = 'config';
}

async function submitForm() {
  const valid = await formRef.value?.validate();
  if (!valid) return;

  // Derive schedule info
  const schedParams: { schedule_type: ScheduleType; schedule_cron: string | undefined } = {
    schedule_type: ScheduleType.MANUAL,
    schedule_cron: undefined,
  };

  if (indexationConfig.value.schedule_cron) {
    schedParams.schedule_type = ScheduleType.CRON;
    schedParams.schedule_cron = indexationConfig.value.schedule_cron;
  }

  // Merge all configs back into data
  const mergedData: Connector = {
    ...data.value,
    name: generalConfig.value.name,
    description: generalConfig.value.description,
    schedule_type: schedParams.schedule_type,
    schedule_cron: schedParams.schedule_cron,
    chunk_size: data.value?.chunk_size,
    chunk_overlap: data.value?.chunk_overlap,
    configuration: {
      ...(data.value?.configuration || {}),
      ...typeSpecificConfig.value,
      ai_provider: indexationConfig.value.ai_provider,
      connector_acl: aclConfig.value,
      indexing_config: {
        use_smart_extraction: indexationConfig.value.use_smart_extraction,
      },
    },
  } as Connector;

  emit('save', { type: props.connectorType, data: mergedData });
}

function handleSave() {
  void submitForm();
}
</script>

<style scoped>
.border-top {
  border-top: 1px solid var(--q-sixth);
}
.border-bottom {
  border-bottom: 1px solid var(--q-sixth);
}

/* Modern Tabs Styling */
.modern-tabs {
  background: transparent;
}

:deep(.modern-tabs .q-tab) {
  border-radius: 8px;
  margin-right: 8px;
  min-height: 36px;
  padding: 0 16px;
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

/* Hide the default ripple for a cleaner feel if desired, or keep it */
:deep(.modern-tabs .q-focus-helper) {
  display: none;
}

/* Vertical Sub-tabs Styling */
:deep(.q-tabs--vertical .q-tab) {
  border-radius: 8px;
  margin-bottom: 8px;
  min-height: 48px;
  padding: 0 16px;
  transition: all 0.3s ease;
  opacity: 0.7;
  border: 1px solid transparent;
  color: var(--q-text-sub);
  justify-content: flex-start;
}

:deep(.q-tabs--vertical .q-tab:hover) {
  opacity: 1;
  background: rgba(255, 255, 255, 0.05);
  color: var(--q-text-main);
}

:deep(.q-tabs--vertical .q-tab--active) {
  opacity: 1;
  background: var(--q-accent);
  color: white !important;
  border-color: var(--q-accent);
  box-shadow: 0 4px 12px rgba(var(--q-accent-rgb), 0.3);
}

:deep(.q-tabs--vertical .q-tab__indicator) {
  display: none;
}
</style>
