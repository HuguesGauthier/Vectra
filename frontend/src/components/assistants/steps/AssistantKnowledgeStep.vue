<template>
  <div class="row justify-center max-width-container">
    <q-card class="col-12 col-md-10 bg-primary">
      <div v-if="!hideTitle" class="text-subtitle1 text-center q-mb-lg">
        {{ $t('linkConnectorsDesc') }}
      </div>

      <div v-if="loadingConnectors" class="row justify-center q-my-xl">
        <q-spinner color="accent" size="3em" />
      </div>

      <!-- No Connectors State -->
      <div v-else-if="connectors.length === 0" class="text-center q-pa-xl">
        <q-icon name="cloud_off" size="64px" class="q-mb-md" />
        <div class="text-h6">{{ $t('noConnectorsFound') }}</div>
        <div class="q-mt-md">{{ $t('addFirstSource') }}</div>
      </div>

      <div v-else>
        <!-- Mixed Providers Warning -->
        <div v-if="mixedProvidersWarning" class="q-mb-md">
          <q-banner rounded class="bg-warning text-dark">
            <template v-slot:avatar>
              <q-icon name="warning" color="dark" />
            </template>
            <div class="text-weight-bold">{{ $t('performanceWarning') }}</div>
            <div>{{ $t('mixedProvidersDesc') }}</div>
          </q-banner>
        </div>

        <!-- Generic Selector Card -->
        <div class="q-mb-md">
          <q-card
            class="cursor-pointer hover-accent bg-secondary non-selectable"
            v-ripple
            @click="openSelector"
            bordered
            style="border: 1px solid var(--q-sixth); border-radius: 8px"
            :style="error ? 'border-color: var(--q-negative) !important' : ''"
          >
            <q-card-section class="row items-center justify-between q-pa-lg">
              <div class="row items-center">
                <q-avatar color="accent" icon="hub" class="q-mr-md shadow-1" text-color="white" />
                <div>
                  <div class="text-h6">{{ $t('selectDataSources') }}</div>
                  <div class="text-caption">
                    {{ selectedConnectors.length }} {{ $t('sourcesSelected') }}
                  </div>
                </div>
              </div>
              <q-icon name="touch_app" size="md" color="grey-6" />
            </q-card-section>
          </q-card>

          <div v-if="error" class="text-negative text-caption q-mt-xs q-pl-xs">
            <q-icon name="error" class="q-mr-xs" />
            {{ errorMessage }}
          </div>
        </div>

        <!-- Selected Connectors Preview -->
        <div class="q-mb-xl">
          <div v-if="selectedConnectors.length > 0" class="row q-gutter-sm justify-center">
            <q-chip
              v-for="conn in selectedConnectors"
              :key="conn.id"
              removable
              @remove="removeConnector(conn.id)"
              color="primary"
              class="shadow-1"
            >
              <q-avatar
                :color="getConnectorConfig(conn.connector_type).color"
                :icon="getConnectorConfig(conn.connector_type).icon"
                size="xs"
                text-color="white"
              />
              <q-avatar size="xs" rounded color="transparent">
                <img :src="getProviderLogo(conn)" />
              </q-avatar>
              {{ conn.name }}
            </q-chip>
          </div>
          <div v-else class="text-center text-grey-6 text-italic q-py-md">
            {{ $t('noSourcesSelectedHint') }}
          </div>
        </div>

        <!-- Access Control List -->
        <div class="q-mt-lg">
          <div class="border-top q-pt-lg">
            <div class="text-h6 q-mb-sm">{{ $t('accessControlList') }}</div>
            <div class="text-subtitle2 q-mb-md">
              {{ $t('accessControlDesc') }}
            </div>

            <div
              v-if="formData.configuration"
              class="bg-secondary q-pa-sm rounded-borders q-mb-md q-field--standout"
              style="
                min-height: 56px;
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                border: 1px solid var(--q-sixth);
              "
            >
              <q-chip
                v-for="tag in formData.configuration.tags"
                :key="tag"
                color="accent"
                size="md"
                class="q-ma-xs"
                text-color="white"
              >
                {{ tag }}
              </q-chip>
            </div>
          </div>
        </div>
      </div>
    </q-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import type { Connector } from 'src/services/connectorService';
import type { Assistant } from 'src/services/assistantService';
import ConnectorSelectionDialog from 'src/components/assistants/dialogs/ConnectorSelectionDialog.vue';
import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';

const $q = useQuasar();
const { t } = useI18n();

const props = defineProps<{
  modelValue: Partial<Assistant>;
  connectors: Connector[];
  availableTags: string[];
  loadingConnectors?: boolean;
  hideTitle?: boolean;
  fullWidth?: boolean; // To allow usage in narrower contexts like drawer
  error?: boolean;
  errorMessage?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

const formData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const selectedConnectors = computed(() => {
  const ids = formData.value.linked_connector_ids || [];
  return props.connectors.filter((c) => ids.includes(c.id));
});

const mixedProvidersWarning = computed(() => {
  const selectedIds = formData.value.linked_connector_ids || [];
  if (selectedIds.length < 2) return false;

  const providers = new Set<string>();
  props.connectors.forEach((conn) => {
    if (selectedIds.includes(conn.id)) {
      const provider = (conn.configuration?.ai_provider as string) || 'unknown';
      providers.add(provider);
    }
  });

  return providers.size > 1;
});

const CONNECTOR_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  local_file: {
    icon: 'file_upload',
    color: 'grey-9',
    label: t('folder'),
  },
  local_folder: {
    icon: 'folder',
    color: 'amber-9',
    label: t('networkName'),
  },
  folder: {
    icon: 'folder',
    color: 'amber-9',
    label: t('folder'),
  },
  confluence: {
    icon: 'img:https://cdn.worldvectorlogo.com/logos/confluence-1.svg',
    color: 'blue-5',
    label: 'Confluence',
  },
  sharepoint: {
    icon: 'cloud_circle',
    color: 'teal-6',
    label: 'SharePoint',
  },
  share_point: {
    icon: 'cloud_circle',
    color: 'teal-6',
    label: 'SharePoint',
  },
  sql: {
    icon: 'storage',
    color: 'blue-9',
    label: 'SQL Server',
  },
  web_crawler: {
    icon: 'public',
    color: 'indigo-5',
    label: 'Web Crawler',
  },
};

function getConnectorConfig(type: string) {
  return (
    CONNECTOR_CONFIG[type] || {
      icon: 'extension',
      color: 'blue-grey-5',
      label: type,
    }
  );
}

function getProviderLogo(conn: Connector) {
  const provider = (conn.configuration?.ai_provider as string) || 'gemini';
  if (provider === 'openai') return openaiLogo;
  if (provider === 'gemini') return geminiLogo;
  if (provider === 'local' || provider === 'ollama') return localLogo;
  return geminiLogo;
}

function openSelector() {
  $q.dialog({
    component: ConnectorSelectionDialog,
    componentProps: {
      connectors: props.connectors,
      selectedIds: formData.value.linked_connector_ids || [],
    },
  }).onOk((newSelection: string[]) => {
    // Update user selection
    // We need to update the model value
    const updated = { ...formData.value };
    updated.linked_connector_ids = newSelection;
    emit('update:modelValue', updated);
  });
}

function removeConnector(id: string) {
  const current = formData.value.linked_connector_ids || [];
  const updatedIds = current.filter((cid) => cid !== id);
  const updated = { ...formData.value };
  updated.linked_connector_ids = updatedIds;
  emit('update:modelValue', updated);
}
</script>

<style scoped>
.hover-accent:hover {
  border-color: var(--q-accent);
  background-color: rgba(var(--q-accent-rgb), 0.05);
}

.border-top {
  border-top: 1px solid var(--q-sixth);
}
</style>
