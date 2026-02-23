<template>
  <q-dialog ref="dialogRef" @hide="onDialogHide">
    <q-card
      class="column full-height bg-primary"
      style="width: 60vw; max-width: 90vw; height: 100vh; max-height: 100vh"
    >
      <!-- Header -->
      <q-card-section class="row items-center q-pb-sm bg-secondary border-bottom">
        <div class="text-h6">{{ $t('selectDataSources') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <!-- Search -->
      <q-card-section class="bg-secondary sticky-header z-top">
        <q-input
          v-model="searchQuery"
          outlined
          dense
          bg-color="secondary"
          input-class="text-main"
          label-color="sub"
          :placeholder="$t('searchConnectors')"
          class="q-my-xs search-input"
        >
          <template v-slot:append>
            <q-icon name="search" />
          </template>
        </q-input>
      </q-card-section>

      <!-- Grid Content -->
      <q-card-section class="col scroll q-pa-md bg-primary">
        <div v-if="filteredConnectors.length === 0" class="flex flex-center q-pa-xl full-height">
          <div class="text-center text-grey-5">
            <q-icon name="search_off" size="64px" class="q-mb-md opacity-50" />
            <div class="text-h6 text-weight-regular">{{ $t('noConnectorsFound') }}</div>
          </div>
        </div>

        <div v-else class="row q-col-gutter-md">
          <div v-for="conn in filteredConnectors" :key="conn.id" class="col-12 col-md-6 col-lg-4">
            <div
              class="connector-card column justify-between full-height"
              :class="{
                selected: localSelectedIds.includes(conn.id),
                disabled: isConnectorDisabled(conn),
              }"
              @click="!isConnectorDisabled(conn) && selectConnector(conn)"
            >
              <!-- Card Header -->
              <div class="row items-start justify-between q-mb-sm">
                <div class="row items-center">
                  <q-avatar
                    :icon="getConnectorConfig(conn.connector_type).icon"
                    size="md"
                    :color="getConnectorConfig(conn.connector_type).color"
                    text-color="white"
                    class="q-mr-sm"
                  >
                    <q-tooltip>{{ getConnectorConfig(conn.connector_type).label }}</q-tooltip>
                  </q-avatar>
                  <q-avatar size="sm" rounded color="transparent">
                    <img :src="getProviderLogo(conn)" />
                    <q-tooltip>{{
                      $t((conn.configuration?.ai_provider as string) || 'local')
                    }}</q-tooltip>
                  </q-avatar>
                </div>
                <q-checkbox
                  v-if="getCategory(conn.connector_type) === 'folder'"
                  :model-value="localSelectedIds.includes(conn.id)"
                  @update:model-value="selectConnector(conn)"
                  color="accent"
                  dense
                  :disable="isConnectorDisabled(conn)"
                />
                <q-radio
                  v-else
                  :model-value="localSelectedIds[0]"
                  :val="conn.id"
                  @update:model-value="selectConnector(conn)"
                  color="accent"
                  dense
                  :disable="isConnectorDisabled(conn)"
                />
              </div>

              <!-- Card Body -->
              <div class="col q-py-sm">
                <div class="text-subtitle1 text-weight-bold ellipsis-2-lines q-mb-xs">
                  {{ conn.name }}
                </div>
                <div class="text-caption text-grey-5 ellipsis-3-lines" style="min-height: 3em">
                  {{ conn.description || $t('noDescription') }}
                </div>
              </div>

              <!-- Card Footer -->
              <div class="row items-center justify-between q-mt-sm pt-2 border-top-dashed">
                <div class="row items-center q-gutter-x-sm">
                  <!-- ACL Badge -->
                  <div class="row q-gutter-x-xs" v-if="getAclTags(conn).length > 0">
                    <q-badge
                      v-for="tag in getAclTags(conn)"
                      :key="tag"
                      color="blue-grey-9"
                      text-color="blue-grey-2"
                      :label="tag"
                      transparent
                      class="text-caption"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>

      <!-- Footer -->
      <q-card-actions align="right" class="bg-secondary border-top q-pa-md z-top">
        <div class="text-subtitle2 q-mr-md">
          <span class="text-accent text-weight-bold">{{ localSelectedIds.length }}</span>
          {{ $t('itemsSelected') }}
        </div>
        <q-btn flat :label="$t('cancel')" color="grey-5" v-close-popup class="q-px-md" />
        <q-btn
          :label="$t('confirmSelection')"
          color="accent"
          @click="onOKClick"
          class="q-px-lg shadow-2"
          no-caps
          :disable="localSelectedIds.length === 0"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';
import { ref, computed } from 'vue';
import { useDialogPluginComponent } from 'quasar';
import { useI18n } from 'vue-i18n';
import type { Connector } from 'src/services/connectorService';

const props = defineProps<{
  connectors: Connector[];
  selectedIds: string[];
}>();

defineEmits([...useDialogPluginComponent.emits]);

const { t } = useI18n();
const { dialogRef, onDialogHide, onDialogOK } = useDialogPluginComponent();

const searchQuery = ref('');
const localSelectedIds = ref<string[]>(props.selectedIds || []);

const currentCategory = computed(() => {
  if (localSelectedIds.value.length === 0) return null;
  const firstId = localSelectedIds.value[0];
  const conn = props.connectors.find((c) => c.id === firstId);
  return conn ? getCategory(conn.connector_type) : null;
});

function getCategory(type: string): 'folder' | 'csv' | 'sql' {
  if (type === 'sql') return 'sql';
  if (type === 'local_file') return 'csv';
  return 'folder';
}

function isConnectorDisabled(conn: Connector) {
  if (localSelectedIds.value.length === 0) return false;
  const category = getCategory(conn.connector_type);
  if (category !== currentCategory.value) return true;
  return false;
}

const filteredConnectors = computed(() => {
  if (!searchQuery.value) return props.connectors;
  const q = searchQuery.value.toLowerCase();
  return props.connectors.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.description?.toLowerCase().includes(q) ||
      c.connector_type.toLowerCase().includes(q),
  );
});

function getProviderLogo(conn: Connector) {
  const provider = (conn.configuration?.ai_provider as string) || 'local';
  if (provider === 'openai') return openaiLogo;
  if (provider === 'gemini') return geminiLogo;
  if (provider === 'local' || provider === 'ollama') return localLogo;
  return localLogo;
}

function getAclTags(conn: Connector): string[] {
  const acl = conn.configuration?.connector_acl;
  return Array.isArray(acl) ? (acl as string[]) : [];
}

const CONNECTOR_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  local_file: {
    icon: 'file_upload',
    color: 'grey-9',
    label: t('csvFile'),
  },
  local_folder: {
    icon: 'folder',
    color: 'amber-9',
    label: t('networkName'),
  },
  folder: {
    // Fallback or alias
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
    // Alias for safety
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

function selectConnector(conn: Connector) {
  const index = localSelectedIds.value.indexOf(conn.id);
  const category = getCategory(conn.connector_type);

  if (index !== -1) {
    localSelectedIds.value.splice(index, 1);
  } else {
    if (category === 'folder') {
      localSelectedIds.value.push(conn.id);
    } else {
      // Single selection for CSV/SQL
      localSelectedIds.value = [conn.id];
    }
  }
}

function onOKClick() {
  onDialogOK(localSelectedIds.value);
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid var(--q-sixth);
}
.border-top {
  border-top: 1px solid var(--q-sixth);
}
.border-top-dashed {
  border-top: 1px dashed var(--q-sixth);
  padding-top: 8px;
}

.sticky-header {
  position: sticky;
  top: 0;
  z-index: 10;
}

.connector-card {
  background: var(--q-secondary);
  border: 1px solid var(--q-sixth);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: hidden;
}

.connector-card:hover {
  background: rgba(255, 255, 255, 0.06);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.2);
}

.connector-card.selected {
  background: rgba(var(--q-accent-rgb), 0.1);
  border-color: var(--q-accent);
  box-shadow:
    0 0 0 1px var(--q-accent),
    0 8px 20px rgba(0, 0, 0, 0.3);
}

.connector-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  filter: grayscale(1);
}

.z-top {
  z-index: 20;
}

:deep(.q-field--outlined .q-field__control):before {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined .q-field__control):after {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined.q-field--focused .q-field__control):after {
  border-color: var(--q-accent) !important;
  border-width: 1px !important;
}
</style>
