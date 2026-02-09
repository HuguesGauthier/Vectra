<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Title Header -->
    <div class="row items-center justify-between q-pt-md q-pb-md q-pl-none q-mb-md">
      <div>
        <div class="text-h4 text-weight-bold">{{ $t('knowledgeBase') }}</div>
        <div class="text-subtitle1 q-pt-xs">{{ $t('manageDataSources') }}</div>
      </div>
    </div>

    <div class="column q-gutter-y-md">
      <!-- Section 1: Data Sources Table -->
      <div>
        <AppTable
          :rows="sortedConnectors"
          :columns="columns"
          :loading="connectorStore.loading"
          v-model:filter="filter"
          :no-data-title="$t('noConnectorsFound')"
          :no-data-message="$t('addFirstSource')"
          no-data-icon="library_add"
        >
          <!-- Top Slot for Toolbar -->
          <!-- Add Button Slot -->
          <template #add-button>
            <q-btn
              color="accent"
              icon="add"
              size="12px"
              round
              unelevated
              @click="openTypeSelection"
            >
              <AppTooltip>{{ $t('createNew') }}</AppTooltip>
            </q-btn>
          </template>

          <template #no-data-action>
            <q-btn
              color="accent"
              size="12px"
              icon="add"
              round
              unelevated
              @click="openTypeSelection"
            />
          </template>

          <!-- Body Slot for Custom Cells -->
          <!-- Body Slot for Custom Cells -->
          <template v-slot:body="{ props }">
            <q-tr :props="props">
              <!-- AI Engine Column (First) -->
              <q-td
                key="ai_engine"
                :props="props"
                v-if="isFirstOfGroup(props.rowIndex)"
                :rowspan="getGroupSize(props.rowIndex)"
                style="vertical-align: middle"
              >
                <q-avatar size="sm" rounded color="transparent">
                  <img :src="getProviderLogo(props.row)" />
                  <AppTooltip>{{
                    $t(props.row.configuration?.ai_provider || 'gemini')
                  }}</AppTooltip>
                </q-avatar>
              </q-td>

              <!-- Type Column (Second) -->
              <q-td
                key="type"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <q-avatar
                  size="sm"
                  :color="getConnectorColor(props.row.connector_type)"
                  :text-color="getConnectorTextColor(props.row.connector_type)"
                  :icon="getConnectorIcon(props.row.connector_type)"
                />
              </q-td>

              <!-- Name Column -->
              <q-td
                key="name"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div
                  class="text-weight-bold cursor-pointer hover-underline"
                  @click="openDocumentsDialog(props.row)"
                >
                  {{ props.row.name }}
                </div>
              </q-td>

              <!-- Description Column -->
              <q-td
                key="description"
                :props="props"
                style="max-width: 300px"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="ellipsis">{{ props.row.description }}</div>
                <AppTooltip v-if="props.row.description && props.row.description.length > 50">
                  {{ props.row.description }}
                </AppTooltip>
              </q-td>

              <!-- ACL Column -->
              <q-td
                key="acl"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="row q-gutter-xs">
                  <q-chip
                    v-for="tag in props.row.configuration?.connector_acl || []"
                    :key="tag"
                    size="xs"
                    color="accent"
                    text-color="grey-3"
                    class="q-ma-none q-mt-xs q-mr-xs"
                  >
                    {{ tag }}
                  </q-chip>
                </div>
              </q-td>

              <q-td
                key="file_count"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="row items-center no-wrap">
                  <q-btn
                    round
                    flat
                    dense
                    size="sm"
                    icon="sync"
                    color="positive"
                    class="q-mr-sm"
                    @click="refreshFiles(props.row)"
                  >
                    <AppTooltip>{{ $t('refreshFiles') }}</AppTooltip>
                  </q-btn>
                  {{ props.row.total_docs_count || 0 }}
                </div>
              </q-td>

              <!-- Schedule Column -->
              <q-td
                key="schedule"
                :props="props"
                class="row items-center justify-left"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="q-mr-md">
                  <q-toggle
                    v-model="props.row.is_enabled"
                    :color="
                      props.row.schedule_type !== 'manual' && props.row.is_enabled
                        ? 'positive'
                        : 'grey'
                    "
                    size="xs"
                    dense
                    :disable="props.row.schedule_type === 'manual'"
                    @update:model-value="(val: boolean | null) => toggleSource(props.row, val)"
                  />
                </div>
                <div>
                  {{
                    props.row.schedule_type === 'manual'
                      ? $t('scheduleManual')
                      : getScheduleLabel(props.row.schedule_cron, t)
                  }}
                </div>
              </q-td>

              <!-- Last Vectorized Column with Play Button -->
              <q-td
                key="last_vectorized"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="row items-center no-wrap">
                  <div class="q-mr-sm">
                    <q-btn
                      v-if="
                        props.row.status === ConnectorStatus.SYNCING ||
                        props.row.status === ConnectorStatus.QUEUED
                      "
                      round
                      flat
                      size="sm"
                      dense
                      icon="stop"
                      color="warning"
                      @click="syncSource(props.row)"
                    >
                      <AppTooltip>{{ $t('stopSync') }}</AppTooltip>
                    </q-btn>

                    <q-btn
                      v-else
                      round
                      flat
                      dense
                      size="sm"
                      icon="play_arrow"
                      color="grey-5"
                      :disable="
                        !props.row.is_enabled ||
                        !props.row.total_docs_count ||
                        props.row.schedule_type !== 'manual'
                      "
                      @click="syncSource(props.row)"
                    >
                      <AppTooltip>
                        {{
                          props.row.schedule_type !== 'manual'
                            ? $t('scheduledSyncOnly')
                            : $t('syncNow')
                        }}
                      </AppTooltip>
                    </q-btn>
                  </div>
                  <div>
                    {{ formatDate(props.row.last_vectorized_at) || $t('neverSynced') }}
                  </div>
                </div>
              </q-td>

              <!-- Status Column -->
              <q-td
                key="status"
                :props="props"
                class="row items-center"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <q-badge
                  v-if="props.row.is_enabled"
                  :color="getStatusColor(props.row.status)"
                  rounded
                  :class="{
                    'cursor-pointer': props.row.status === ConnectorStatus.ERROR,
                  }"
                  @click="showError(props.row)"
                >
                  <q-icon
                    :name="getStatusIcon(props.row.status)"
                    size="8px"
                    class="q-mr-xs"
                    :class="{
                      'fa-spin': props.row.status === ConnectorStatus.SYNCING,
                    }"
                  />
                  {{ getStatusLabel(props.row.status) }}
                </q-badge>
                <q-badge v-else color="grey" outline rounded :label="$t('disabled')" />

                <!-- Progress Bar -->
                <div
                  v-if="props.row.status === ConnectorStatus.VECTORIZING"
                  class="q-ma-xs no-wrap row items-center"
                  style="width: 120px"
                >
                  <q-linear-progress
                    :value="
                      props.row.sync_total
                        ? (props.row.sync_current || 0) / props.row.sync_total
                        : props.row.total_docs_count
                          ? props.row.indexed_docs_count / props.row.total_docs_count
                          : 0
                    "
                    rounded
                    size="6px"
                  />
                  <div class="text-caption text-right q-ma-xs" style="font-size: 10px">
                    {{
                      props.row.sync_total ? props.row.sync_current : props.row.indexed_docs_count
                    }}
                    /
                    {{ props.row.sync_total ? props.row.sync_total : props.row.total_docs_count }}
                  </div>
                </div>
              </q-td>

              <!-- Actions Column -->
              <q-td
                key="actions"
                :props="props"
                :class="{ 'group-separator': isLastOfGroup(props.rowIndex) }"
              >
                <div class="row items-center q-gutter-x-sm">
                  <!-- Documents Dialog Button -->
                  <q-btn
                    round
                    flat
                    dense
                    size="sm"
                    icon="playlist_add"
                    @click="openDocumentsDialog(props.row)"
                  >
                    <AppTooltip>{{ $t('viewDocuments') }}</AppTooltip>
                  </q-btn>

                  <q-btn
                    round
                    flat
                    dense
                    size="sm"
                    icon="edit"
                    @click="openDrawerViaDataSource(props.row)"
                  >
                    <AppTooltip>{{ $t('edit') }}</AppTooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    dense
                    size="sm"
                    icon="delete"
                    color="negative"
                    @click="confirmDelete(props.row)"
                  >
                    <AppTooltip>{{ $t('delete') }}</AppTooltip>
                  </q-btn>
                </div>
              </q-td>
            </q-tr>
          </template>
        </AppTable>
      </div>

      <!-- Drawer -->
      <ConnectorDrawer
        v-if="selectedType"
        v-model="isDrawerOpen"
        :connector-type="selectedType"
        :data="
          theConnectors.editingConnector ||
          new Connector({ connector_type: mapUiTypeToBackend(selectedType) })
        "
        :title="drawerTitle"
        :loading="isSaving"
        @save="onConnectorSaved"
      />

      <AddConnectorStepper
        v-model:isOpen="isStepperOpen"
        :loading="isSaving"
        @save="onConnectorSaved"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { date, type QTableColumn } from 'quasar';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import { Connector, getScheduleLabel, type ConnectorSavePayload } from 'src/models/Connector';
import { ConnectorStatus, ConnectorType } from 'src/models/enums';
import ConnectorDrawer from 'src/components/connectors/ConnectorDrawer.vue';
import AddConnectorStepper from 'src/components/connectors/AddConnectorStepper.vue';
import AppTooltip from 'components/common/AppTooltip.vue';
import AppTable from 'components/common/AppTable.vue';
import { useConnectorStore } from 'src/stores/ConnectorStore';
import { useConnectorActions } from 'src/composables/useConnectorActions';
import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';

// --- DEFINITIONS ---
defineOptions({
  name: 'ConnectorsPage',
});

// --- STATE ---
const { t } = useI18n();
const { notify } = useNotification();
const router = useRouter();
const connectorStore = useConnectorStore();
const {
  isSaving,
  handleSaveConnector,
  handleDeleteConnector,
  handleToggleConnector,
  handleSyncConnector,
  handleScanFiles,
} = useConnectorActions();

// UI state
const theConnectors = reactive({
  // Mapped to store for template compatibility, or use store directly:
  // We'll trust the store.connectors is reactive
  selected: null as Connector | null, // Original connector (for list and comparison)
  editingConnector: null as Connector | null, // Copy for the drawer
  refreshTimer: null as ReturnType<typeof setInterval> | null,
});

// UI state
const isStepperOpen = ref(false);
const isDrawerOpen = ref(false);
// isSaving handled by composable
const selectedType = ref<string>('');
const filter = ref('');
// Types for local usage
interface UiConnectorType {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  textColor: string;
}

// --- COMPUTED ---
const sortedConnectors = computed(() => {
  const list = [...connectorStore.connectors];
  return list.sort((a, b) => {
    // 1. AI Provider
    const providerA = a.configuration?.ai_provider || 'gemini';
    const providerB = b.configuration?.ai_provider || 'gemini';
    if (providerA !== providerB) return providerA.localeCompare(providerB);

    // 2. Connector Type
    if (a.connector_type !== b.connector_type)
      return a.connector_type.localeCompare(b.connector_type);

    // 3. Name
    return a.name.localeCompare(b.name);
  });
});

/**
 * Pre-calculated row metadata for grouping.
 * Map<RowIndex, { isFirst: boolean, rowSpan: number, isLast: boolean }>
 */
const rowMetadata = computed(() => {
  const map = new Map<number, { isFirst: boolean; rowSpan: number; isLast: boolean }>();
  const list = sortedConnectors.value;
  const n = list.length;

  for (let i = 0; i < n; i++) {
    const current = list[i];
    if (!current) continue;
    const currProvider = current.configuration?.ai_provider || 'gemini';

    // Check Previous
    const prev = list[i - 1];
    const prevProvider = prev?.configuration?.ai_provider || 'gemini';
    const isFirst = i === 0 || currProvider !== prevProvider;

    // Check Next
    const next = list[i + 1];
    const nextProvider = next?.configuration?.ai_provider || 'gemini';
    const isLast = i === n - 1 || currProvider !== nextProvider;

    // Calculate RowSpan (only if first)
    let rowSpan = 1;
    if (isFirst) {
      for (let j = i + 1; j < n; j++) {
        const p = list[j]?.configuration?.ai_provider || 'gemini';
        if (p === currProvider) rowSpan++;
        else break;
      }
    }

    map.set(i, { isFirst, rowSpan, isLast });
  }
  return map;
});

// Helper proxies for template to use the computed map
function isFirstOfGroup(rowIndex: number) {
  return rowMetadata.value.get(rowIndex)?.isFirst || false;
}

function getGroupSize(rowIndex: number) {
  return rowMetadata.value.get(rowIndex)?.rowSpan || 1;
}

function isLastOfGroup(rowIndex: number) {
  return rowMetadata.value.get(rowIndex)?.isLast || false;
}

const columns = computed<QTableColumn[]>(() => [
  {
    name: 'ai_engine',
    required: true,
    label: t('aiEngine'),
    align: 'center',
    field: (row: Connector) => row.configuration?.ai_provider || 'gemini',
    sortable: false,
    style: 'color: var(--q-text-main); width: 30px;',
    headerStyle: 'color: var(--q-text-main); width: 30px;',
  },
  {
    name: 'type',
    required: true,
    label: 'Type',
    align: 'center',
    field: (row: Connector) => row.connector_type,
    sortable: false,
    style: 'color: var(--q-text-main); width: 30px;',
    headerStyle: 'color: var(--q-text-main); width: 30px;',
  },
  {
    name: 'name',
    required: true,
    label: t('name'),
    align: 'left',
    field: (row: Connector) => row.name,
    sortable: false,
    style: 'color: var(--q-text-main); width: 150px;',
    headerStyle: 'color: var(--q-text-main); width: 150px;',
  },
  {
    name: 'description',
    align: 'left',
    label: t('description'),
    field: (row: Connector) => row.description,
    sortable: false,
    style: 'color: var(--q-text-main); width: 200px;',
    headerStyle: 'color: var(--q-text-main); width: 200px;',
  },
  {
    name: 'acl',
    align: 'left',
    label: t('acl'),
    field: (row: Connector) => row.configuration?.connector_acl,
    sortable: false,
    style: 'color: var(--q-text-main); width: 50px;',
    headerStyle: 'color: var(--q-text-main); width: 50px;',
  },
  {
    name: 'file_count',
    align: 'left',
    label: t('fileCount'),
    field: (row: Connector) => row.total_docs_count,
    sortable: false,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'schedule',
    align: 'left',
    label: t('schedule'),
    field: (row: Connector) => row.schedule_type,
    sortable: false,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },

  {
    name: 'last_vectorized',
    align: 'left',
    label: t('lastVectorized'),
    field: (row: Connector) => row.last_vectorized_at,
    sortable: false,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'status',
    align: 'left',
    label: t('status'),
    field: (row: Connector) => row.status,
    sortable: false,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'actions',
    align: 'left',
    label: '',
    field: 'actions',
    sortable: false,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
]);

// Available connector types configuration
const connectorTypes = computed<UiConnectorType[]>(() => [
  {
    id: 'file',
    name: t('folder'),
    description: t('folderDesc'),
    icon: 'file_upload',
    color: 'grey-5',
    textColor: 'grey-10',
  },
  {
    id: 'folder',
    name: t('networkName'),
    description: t('networkDesc'),
    icon: 'folder',
    color: 'amber-2',
    textColor: 'amber-7',
  },
  {
    id: 'sql',
    name: t('sql'),
    description: t('sqlDesc'),
    icon: 'storage',
    color: 'blue-9',
    textColor: 'white',
  },
  {
    id: 'vanna_sql',
    name: t('vannaSql'),
    description: t('vannaSqlDesc'),
    icon: 'psychology',
    color: 'deep-purple-6',
    textColor: 'white',
  },
]);

// Dynamic title for the drawer based on selection
const drawerTitle = computed(() => {
  const type = connectorTypes.value.find((t) => t.id === selectedType.value);
  const typeName = type ? type.name : 'Connector';
  return theConnectors.selected
    ? t('editConnector', { type: theConnectors.selected.name })
    : t('addConnector', { type: typeName });
});

// --- WATCHERS ---

onMounted(async () => {
  // Initial load
  if (connectorStore.connectors.length === 0) {
    await connectorStore.fetchAll();
  }
});

onUnmounted(() => {
  if (theConnectors.refreshTimer) {
    clearInterval(theConnectors.refreshTimer);
    theConnectors.refreshTimer = null;
  }
});

// --- FUNCTIONS ---

function mapUiTypeToBackend(uiType: string): ConnectorType {
  if (uiType === 'file') return ConnectorType.LOCAL_FILE;
  if (uiType === 'folder') return ConnectorType.LOCAL_FOLDER;
  return uiType as unknown as ConnectorType;
}

function mapBackendToUiType(connector: Connector): string {
  if (connector.connector_type === ConnectorType.LOCAL_FOLDER) return 'folder';
  if (connector.connector_type === ConnectorType.LOCAL_FILE) {
    // Legacy support: If it has a path but is marked layout_file, might be old folder?
    // But usually 'file' type is for unrelated uploads.
    // Let's assume strict mapping for now or keep fallback if needed.
    // If we want to be safe:
    if (connector.configuration?.path && !connector.connector_type.includes('folder')) {
      // This was the old heuristic. We can keep it or simpler:
      return 'file';
    }
    return 'file';
  }
  return connector.connector_type;
}

/**
 * Opens the drawer to edit an existing data source.
 * @param {Connector} source - The connector to edit.
 */
function openDrawerViaDataSource(source: Connector) {
  selectedType.value = mapBackendToUiType(source);
  theConnectors.selected = source; // Keep ref to original
  theConnectors.editingConnector = new Connector(source); // Deep clone for editing
  // Ensure config is also cloned
  if (source.configuration) {
    theConnectors.editingConnector.configuration = JSON.parse(JSON.stringify(source.configuration));
  }
  isDrawerOpen.value = true;
}

/**
 * Opens the documents page for a specific connector.
 * @param {Connector} source - The connector to view documents for.
 */
function openDocumentsDialog(source: Connector) {
  void router.push({ name: 'ConnectorDocuments', params: { id: source.id } });
}

/**
 * Opens the type selection dialog for creating a new connector.
 */
function openTypeSelection() {
  // Clear any previous selection to ensure we are in CREATE mode
  theConnectors.selected = null;
  theConnectors.editingConnector = null;
  selectedType.value = '';

  // connectorTypeFilter.value = '';
  // isTypeSelectionOpen.value = true;
  isStepperOpen.value = true;
}

/**
 * Handles the save event from the connector drawer.
 * Creates or updates the connector via the service.
 * @param {ConnectorSavePayload} payload - The payload containing type and data.
 */
async function onConnectorSaved(payload: ConnectorSavePayload) {
  await handleSaveConnector(payload, theConnectors.selected, () => {
    isDrawerOpen.value = false;
    isStepperOpen.value = false;
  });
}

/**
 * Confirms and executes the deletion of a connector.
 * @param {Connector} connector - The connector to delete.
 */
function confirmDelete(connector: Connector) {
  handleDeleteConnector(connector);
}

/**
 * Toggles the enabled state of a source.
 * @param {Connector} source - The connector to toggle.
 * @param {boolean | null} val - The new enabled state (from q-toggle).
 */
function toggleSource(source: Connector, val: boolean | null) {
  void handleToggleConnector(source, val);
}

/**
 * Triggers a manual sync for a source.
 */
function syncSource(source: Connector, force = false) {
  void handleSyncConnector(source, force);
}

/**
 * Displays the error message for a failed connector using the notification system.
 * @param {Connector} source - The connector to check.
 */
function showError(source: Connector) {
  if (source.status === ConnectorStatus.ERROR && source.last_error) {
    notify({
      type: 'negative',
      message: source.last_error,
      timeout: 0, // Persistent until dismissed
      actions: [
        {
          label: t('dismiss'),
          color: 'white',
          handler: () => {
            /* close */
          },
        },
      ],
    });
  }
}

/**
 * Returns the color associated with a specific connector status.
 * @param {ConnectorStatus} status - The status to check.
 * @returns {string} The Quasar color name.
 */
function getStatusColor(status: ConnectorStatus) {
  switch (status) {
    case ConnectorStatus.QUEUED:
      return 'secondary';
    case ConnectorStatus.SYNCING:
      return 'positive';
    case ConnectorStatus.IDLE:
      return 'grey-7';
    case ConnectorStatus.ERROR:
      return 'negative';
    case ConnectorStatus.PAUSED:
      return 'warning';

    // Legacy support or fallback
    case ConnectorStatus.STARTING:
      return 'positive';
    case ConnectorStatus.VECTORIZING:
      return 'positive';

    default:
      return 'grey';
  }
}

/**
 * Returns the icon name for a specific connector status.
 * @param {ConnectorStatus} status - The status to check.
 * @returns {string} The Material Design icon name.
 */
function getStatusIcon(status: ConnectorStatus) {
  switch (status) {
    case ConnectorStatus.QUEUED:
      return 'hourglass_empty';
    case ConnectorStatus.SYNCING:
      return 'sync';
    case ConnectorStatus.IDLE:
      return 'pause';
    case ConnectorStatus.ERROR:
      return 'error';
    case ConnectorStatus.PAUSED:
      return 'pause_circle';

    default:
      return 'help';
  }
}

/**
 * Triggers a manual file scan/refresh for a folder connector.
 * @param {Connector} source - The connector to refresh.
 */
function refreshFiles(source: Connector) {
  void handleScanFiles(source);
}

/**
 * Returns a human-readable label for the status.
 * @param {ConnectorStatus | undefined} status - The status to format.
 * @returns {string} The status label.
 */
function getStatusLabel(status: ConnectorStatus | undefined) {
  if (!status) return t('unknown');
  return t(status);
}

/**
 * Returns the icon associated with a connector type.
 * @param {string} type - The connector type ID.
 * @returns {string} The icon name.
 */
function getConnectorIcon(type: string) {
  let t = connectorTypes.value.find((ct) => ct.id === type);
  if (!t) {
    if (type === ConnectorType.LOCAL_FOLDER)
      t = connectorTypes.value.find((ct) => ct.id === 'folder');
    if (type === ConnectorType.LOCAL_FILE) t = connectorTypes.value.find((ct) => ct.id === 'file');
  }
  return t ? t.icon : 'extension';
}

/**
 * Returns the background color for a connector type.
 * @param {string} type - The connector type ID.
 * @returns {string} The color name.
 */
function getConnectorColor(type: string) {
  let t = connectorTypes.value.find((ct) => ct.id === type);
  if (!t) {
    if (type === ConnectorType.LOCAL_FOLDER)
      t = connectorTypes.value.find((ct) => ct.id === 'folder');
    if (type === ConnectorType.LOCAL_FILE) t = connectorTypes.value.find((ct) => ct.id === 'file');
  }
  return t ? t.color : 'grey';
}

/**
 * Returns the text color for a connector type.
 * @param {string} type - The connector type ID.
 * @returns {string} The text color name.
 */
function getConnectorTextColor(type: string) {
  let t = connectorTypes.value.find((ct) => ct.id === type);
  if (!t) {
    if (type === ConnectorType.LOCAL_FOLDER)
      t = connectorTypes.value.find((ct) => ct.id === 'folder');
    if (type === ConnectorType.LOCAL_FILE) t = connectorTypes.value.find((ct) => ct.id === 'file');
  }
  return t ? t.textColor : 'white';
}

/**
 * Formats a date string into a standard display format.
 * @param {string | undefined} val - The date string to format.
 * @returns {string} The formatted date string.
 */
function formatDate(val: string | undefined) {
  if (!val) return '';
  return date.formatDate(val, 'YYYY-MM-DD HH:mm:ss');
}

/**
 * Returns the logo associated with the connector's AI provider.
 * @param {Connector} connector - The connector to check.
 * @returns {string} The imported SVG logo.
 */
function getProviderLogo(connector: Connector): string {
  const provider = connector.configuration?.ai_provider || 'gemini';
  switch (provider) {
    case 'openai':
      return openaiLogo;
    case 'local':
      return localLogo;
    case 'gemini':
    default:
      return geminiLogo;
  }
}
</script>

<style scoped>
.custom-search :deep(.q-field__control):before,
.custom-search :deep(.q-field__control):after {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

.custom-search :deep(.q-field__control) {
  border-radius: 8px;
}
.q-table__card {
  background-color: var(--q-fourth);
  border-radius: 8px;
}

.hover-underline:hover {
  text-decoration: underline;
}
</style>
