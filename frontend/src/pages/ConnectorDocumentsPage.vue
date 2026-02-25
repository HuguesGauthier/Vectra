<template>
  <q-page class="bg-primary q-pa-md">
    <!-- Back Button -->
    <div class="row items-center q-mb-lg">
      <q-btn
        round
        unelevated
        color="accent"
        icon="arrow_back"
        @click="router.push({ name: 'Connectors' })"
      >
        <AppTooltip>{{ $t('back') }}</AppTooltip>
      </q-btn>
    </div>

    <div class="column q-gutter-y-md">
      <div>
        <AppTable
          :rows="documents"
          :columns="columns"
          :loading="loading"
          v-model:pagination="pagination"
          @request="onRequest"
          :no-data-title="$t('noDocumentsFound')"
          :no-data-message="$t('noDocumentsDesc')"
          no-data-icon="description"
          :filter="search"
          :show-search="false"
        >
          <template v-slot:top-left>
            <!-- Filter Bar -->
            <div class="row items-center q-gutter-x-sm">
              <q-btn
                v-if="
                  connector?.connector_type === ConnectorType.LOCAL_FILE &&
                  !connector?.configuration?.path
                "
                color="accent"
                icon="add"
                unelevated
                round
                dense
                class="q-px-sm"
                @click="openAddDrawer"
              >
                <AppTooltip>{{ $t('addFile') }}</AppTooltip>
              </q-btn>
              <q-input
                v-model="search"
                dense
                outlined
                bg-color="primary"
                class="custom-search"
                :placeholder="$t('searchFile')"
                @update:model-value="onRequestInput"
                style="width: 300px"
              >
                <template v-slot:append>
                  <q-icon name="search" />
                </template>
              </q-input>
            </div>
          </template>

          <!-- Body Slot -->
          <template v-slot:body="{ props }">
            <q-tr :props="props">
              <!-- Status Column -->
              <q-td key="status" :props="props">
                <q-icon
                  :name="getStatusIcon(props.row.status)"
                  :color="getStatusColor(props.row.status)"
                  size="sm"
                >
                  <AppTooltip>{{ props.row.status }}</AppTooltip>
                </q-icon>
              </q-td>

              <!-- Filename Column -->
              <q-td key="file_name" :props="props">
                <div style="max-width: 300px; white-space: normal; word-break: break-all">
                  {{ props.row.file_name }}
                </div>
                <div class="text-caption" v-if="props.row.file_path !== props.row.file_name">
                  {{ props.row.file_path }}
                </div>
                <div v-if="props.row.status === 'processing'" class="q-mt-xs">
                  <q-linear-progress
                    :value="
                      props.row.chunks_total
                        ? (props.row.chunks_processed || 0) / props.row.chunks_total
                        : undefined
                    "
                    :indeterminate="!props.row.chunks_total"
                    color="accent"
                    track-color="dark"
                    rounded
                    size="6px"
                  />
                  <div class="text-caption text-right" style="font-size: 10px">
                    {{
                      props.row.chunks_total
                        ? `${props.row.chunks_processed || 0} / ${props.row.chunks_total}`
                        : props.row.status_details || $t('processing')
                    }}
                  </div>
                </div>
              </q-td>

              <!-- Size Column -->
              <q-td key="file_size" :props="props">
                {{ formatBytes(props.row.file_size, 2, $tm('fileSizeUnits') as string[]) }}
              </q-td>

              <!-- Tokens Column -->
              <q-td key="tokens" :props="props">
                <q-badge
                  color="accent"
                  outline
                  v-if="props.row.doc_token_count"
                  class="cursor-pointer"
                  @click="showCost = !showCost"
                >
                  <template v-if="!showCost"> {{ props.row.doc_token_count }} t </template>
                  <template v-else>
                    {{ formatCost(props.row.doc_token_count) }}
                  </template>
                </q-badge>
              </q-td>

              <!-- Vectors Column -->
              <q-td key="vectors" :props="props">
                {{ props.row.vector_point_count }}
              </q-td>

              <!-- Time Column -->
              <q-td key="last_vectorized" :props="props">
                {{ formatDate(props.row.last_vectorized_at) }}
              </q-td>

              <!-- Actions Column -->
              <q-td key="actions" :props="props">
                <div class="row items-center justify-end q-gutter-x-sm no-wrap">
                  <q-btn
                    v-if="props.row.status === 'processing'"
                    flat
                    dense
                    round
                    icon="stop"
                    size="sm"
                    color="negative"
                    @click="stopDocument(props.row)"
                  >
                    <AppTooltip>{{ $t('stop') }}</AppTooltip>
                  </q-btn>
                  <q-btn
                    v-else
                    flat
                    dense
                    round
                    icon="play_arrow"
                    size="sm"
                    color="grey-5"
                    :disable="props.row.status === 'unsupported'"
                    @click="syncDocument(props.row)"
                  >
                    <AppTooltip>{{ $t('syncNow') }}</AppTooltip>
                  </q-btn>

                  <q-btn
                    flat
                    dense
                    round
                    icon="delete"
                    size="sm"
                    color="negative"
                    @click="deleteDocument(props.row)"
                  >
                    <AppTooltip>{{ $t('delete') }}</AppTooltip>
                  </q-btn>
                </div>
              </q-td>
            </q-tr>
          </template>
        </AppTable>
      </div>

      <!-- Drawer for Adding Files -->
      <q-dialog v-model="drawerOpen" position="right" maximized>
        <q-card class="text-grey-5 bg-primary full-height" style="min-width: 500px">
          <q-card-section>
            <div class="text-h6">{{ newDocument.id ? $t('editFile') : $t('addFile') }}</div>
          </q-card-section>

          <q-card-section class="q-pt-none bg-primary">
            <DocumentFileForm
              v-model:data="newDocument"
              :accept="connector?.connector_type === ConnectorType.LOCAL_FILE ? '.csv' : '*'"
              @save="onSaveDocumentConnector"
              @cancel="drawerOpen = false"
            />
          </q-card-section>
        </q-card>
      </q-dialog>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { date, useQuasar, type QTableColumn } from 'quasar';

import {
  connectorDocumentService,
  type ConnectorDocument,
  type ConnectorDocumentCreate,
} from 'src/services/connectorDocumentService';
import { useConnectorStore } from 'src/stores/ConnectorStore';
import { useConnectorDocumentStore } from 'src/stores/ConnectorDocumentStore';
import type { Connector } from 'src/models/Connector';
import { DocStatus, ConnectorType } from 'src/models/enums';
import DocumentFileForm from 'components/connectors/forms/DocumentFileForm.vue';
import AppTooltip from 'components/common/AppTooltip.vue';
import AppTable from 'components/common/AppTable.vue';
import { useNotification } from 'src/composables/useNotification';
import { useDialog } from 'src/composables/useDialog';
import { storeToRefs } from 'pinia';

// --- DEFINITIONS ---
defineOptions({
  name: 'ConnectorDocumentsPage',
});

const route = useRoute();
const router = useRouter();

const i18n = useI18n();
const { t } = i18n;
const $q = useQuasar();
const { notifySuccess, notifyBackendError } = useNotification();
const { confirm } = useDialog();
const connectorStore = useConnectorStore();
const docStore = useConnectorDocumentStore();
const { documents, loading, pagination, search } = storeToRefs(docStore);

const connectorId = route.params.id as string;
const connector = ref<Connector | null>(null);

const drawerOpen = ref(false);
const newDocument = ref<Partial<ConnectorDocument>>({});

// --- COST TOGGLE ---
const showCost = ref(false);

function formatCost(tokens?: number) {
  if (!tokens) return '$0.00';
  // Use store helper which uses dynamic pricing
  const cost = docStore.getCost(tokens); // We could pass model name if available in doc

  if (cost < 0.01) {
    // Show more precision for tiny amounts
    return `$${cost.toFixed(4)}`;
  }
  return `$${cost.toFixed(2)}`;
}

// --- COMPUTED ---
const columns = computed<QTableColumn[]>(() => [
  {
    name: 'status',
    label: t('status'),
    field: 'status',
    align: 'center',
    sortable: true,
    style: 'color: var(--q-text-main); width: 30px;',
    headerStyle: 'color: var(--q-text-main); width: 30px;',
  },
  {
    name: 'file_name',
    label: t('name'),
    field: 'file_name',
    align: 'left',
    sortable: true,
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },

  {
    name: 'file_size',
    label: t('size'),
    field: 'file_size',
    format: (val: number) => formatBytes(val, 2, i18n.tm('fileSizeUnits')),
    align: 'right',
    sortable: true,
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },
  {
    name: 'tokens',
    label: t('tokens'),
    field: 'doc_token_count',
    align: 'right',
    sortable: true,
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },
  {
    name: 'vectors',
    label: t('vectors'),
    field: 'vector_point_count',
    align: 'right',
    sortable: true,
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },
  {
    name: 'last_vectorized',
    label: t('lastVectorized'),
    field: 'last_vectorized_at',
    align: 'right',
    sortable: true,
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },
  {
    name: 'actions',
    label: '',
    field: 'actions',
    align: 'right',
    style: 'color: var(--q-text-main);',
    headerStyle: 'color: var(--q-text-main);',
  },
]);

// --- LIFECYCLE ---
onMounted(async () => {
  window.addEventListener('doc-progress', handleDocProgress as EventListener);
  window.addEventListener('doc-update', handleDocUpdate as EventListener);
  window.addEventListener('doc-created', handleDocCreated as EventListener);
  window.addEventListener('doc-deleted', handleDocDeleted as EventListener);
  window.addEventListener('keydown', handleKeydown);

  await loadConnector();
  await onRequest();
});

onUnmounted(() => {
  window.removeEventListener('doc-progress', handleDocProgress as EventListener);
  window.removeEventListener('doc-update', handleDocUpdate as EventListener);
  window.removeEventListener('doc-created', handleDocCreated as EventListener);
  window.removeEventListener('doc-deleted', handleDocDeleted as EventListener);
  window.removeEventListener('keydown', handleKeydown);
});

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && !drawerOpen.value) {
    void router.push({ name: 'Connectors' });
  }
}

// --- FUNCTIONS ---

/**
 * Loads the connector details.
 * Tries to find it in the store, otherwise triggers a fetch.
 */
async function loadConnector() {
  // Try to find in store first
  const existing = connectorStore.getConnectorById(connectorId);
  if (existing) {
    connector.value = existing;
  } else {
    // Fallback if not loaded
    await connectorStore.fetchAll(true);
    connector.value = connectorStore.getConnectorById(connectorId) || null;
  }
}

/**
 * Updates the search filter in the store and triggers a reload.
 * @param {string | number | null} val - The search term.
 */
function onRequestInput(val: string | number | null) {
  if (typeof val === 'string') {
    docStore.setSearch(val);
    void onRequest();
  }
}

/**
 * Handles table request (pagination/sorting).
 * @param {Object} requestProp - Pagination details from the table.
 */
async function onRequest(requestProp?: { pagination: { page: number; rowsPerPage: number } }) {
  const { page, rowsPerPage } = requestProp?.pagination || pagination.value;
  // Update local pagination ref if table updates it, although store handles it
  // But wait, v-model:pagination is linked to storeToRefs(docStore).pagination
  // So we just need to call fetch

  await docStore.fetchDocuments(connectorId, page, rowsPerPage);
}

/**
 * Opens the drawer to add a new file.
 */
function openAddDrawer() {
  newDocument.value = { configuration: {} }; // Reset
  drawerOpen.value = true;
}

/**
 * Saves changes.
 */

/**
 * Saves changes.
 */
async function onSaveDocumentConnector() {
  if (!connector.value) return;

  try {
    $q.loading.show();

    const isUpdate = !!newDocument.value.id;
    const filePath = newDocument.value.file_path;
    const fileName = newDocument.value.file_name || filePath?.split('/').pop() || 'unknown';

    if (!filePath) throw new Error('File path required');

    const config = newDocument.value.configuration || undefined;

    if (isUpdate && newDocument.value.id) {
      // Update
      const updatePayload: {
        file_path: string;
        file_name: string;
        configuration?: Record<string, unknown>;
      } = {
        file_path: filePath,
        file_name: fileName,
      };
      if (config) updatePayload.configuration = config;

      await connectorDocumentService.updateDocument(
        connector.value.id,
        newDocument.value.id,
        updatePayload,
      );
      notifySuccess(t('documentUpdated', 'Document updated successfully'));
    } else {
      // Create
      const createPayload: ConnectorDocumentCreate = {
        file_path: filePath,
        file_name: fileName,
      };
      if (newDocument.value.file_size) {
        createPayload.file_size = newDocument.value.file_size;
      }
      if (config) createPayload.configuration = config;

      await connectorDocumentService.createDocument(connector.value.id, createPayload);
      notifySuccess(t('documentAdded', 'Document added successfully'));
    }

    $q.loading.hide();
    drawerOpen.value = false;
  } catch (e: unknown) {
    $q.loading.hide();
    const err = e as { response?: { data?: { code?: string } } };

    // Check for CSV validation errors and reset the form
    if (
      err.response?.data?.code === 'csv_id_column_missing' ||
      err.response?.data?.code === 'csv_id_column_not_unique'
    ) {
      // Reset the document form to allow user to upload a corrected file
      newDocument.value = { configuration: {} };
      return;
    }

    notifyBackendError(e, t('failedToSaveDocument', 'Failed to save document'));
  }
}

/**
 * Triggers synchronization for a specific document.
 * @param {ConnectorDocument} doc - The document to sync.
 */
async function syncDocument(doc: ConnectorDocument) {
  try {
    await docStore.syncDocument(connectorId, doc.id);
    notifySuccess(t('syncStarted', { name: doc.file_name }));
  } catch {
    // Global interceptor
  }
}

/**
 * Stop synchronization for a specific document.
 * @param {ConnectorDocument} doc - The document to stop.
 */
async function stopDocument(doc: ConnectorDocument) {
  try {
    await connectorDocumentService.stopDocument(connectorId, doc.id);
    notifySuccess(t('stopRequested', { name: doc.file_name }));
    // Optimistically update status to paused or similar if needed, but store should handle update
  } catch {
    // Global interceptor
  }
}

/**
 * Deletes a document after confirmation.
 * @param {ConnectorDocument} doc - The document to delete.
 */
function deleteDocument(doc: ConnectorDocument) {
  confirm({
    title: t('confirmDeletion'),
    message: t('confirmDeletionMessage', { name: doc.file_name }),
    confirmLabel: t('delete'),
    confirmColor: 'negative',
    onConfirm: () => {
      void (async () => {
        try {
          await docStore.deleteDocument(connectorId, doc.id);
          notifySuccess(t('documentDeleted'));
        } catch {
          // Global interceptor
        }
      })();
    },
  });
}

// Helpers
function getStatusColor(status: string) {
  switch (status as DocStatus) {
    case DocStatus.INDEXED:
      return 'positive';
    case DocStatus.PROCESSING:
      return 'info';
    case DocStatus.FAILED:
      return 'negative';
    case DocStatus.PENDING:
      return 'grey-7';
    case DocStatus.IDLE:
      return 'grey-7';
    case DocStatus.SKIPPED:
      return 'warning';
    case DocStatus.UNSUPPORTED:
      return 'warning';
    case DocStatus.PAUSED:
      return 'grey-7';
    default:
      return 'grey';
  }
}

function getStatusIcon(status: string) {
  switch (status as DocStatus) {
    case DocStatus.INDEXED:
      return 'check_circle';
    case DocStatus.PROCESSING:
      return 'sync';
    case DocStatus.FAILED:
      return 'error';
    case DocStatus.PENDING:
      return 'hourglass_empty';
    case DocStatus.IDLE:
      return 'hourglass_disabled';
    case DocStatus.SKIPPED:
      return 'fast_forward';
    case DocStatus.UNSUPPORTED:
      return 'block';
    case DocStatus.PAUSED:
      return 'pause';
    default:
      return 'help';
  }
}

function formatDate(val?: string) {
  if (!val) return '';
  return date.formatDate(val, 'YYYY-MM-DD HH:mm:ss');
}

function formatBytes(bytes: number, decimals = 2, units: string[]) {
  // Fallback if units are missing
  const safeUnits = units && units.length > 0 ? units : ['B', 'KB', 'MB', 'GB', 'TB'];

  if (!bytes) return '0 ' + safeUnits[1]; // Return 0 KB/Ko

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  // Logic: Always show at least KB/Ko.
  let unitIndex = i;
  if (unitIndex < 1) unitIndex = 1; // Force KB/Ko

  if (unitIndex >= safeUnits.length) unitIndex = safeUnits.length - 1;

  const val = parseFloat((bytes / Math.pow(k, unitIndex)).toFixed(dm));
  return val + ' ' + safeUnits[unitIndex];
}

function handleDocProgress(event: Event) {
  const customEvent = event as CustomEvent;
  const { doc_id, processed, total } = customEvent.detail;
  docStore.updateDocumentProgress(doc_id, processed, total);
}

function handleDocUpdate(event: Event) {
  const customEvent = event as CustomEvent;
  const {
    id,
    status,
    doc_token_count,
    vector_point_count,
    updated_at,
    details,
    last_vectorized_at,
  } = customEvent.detail;

  docStore.updateDocumentStatus(
    id,
    status,
    doc_token_count,
    vector_point_count,
    updated_at,
    details,
    last_vectorized_at,
  );
}

function handleDocCreated(event: Event) {
  const customEvent = event as CustomEvent;
  const doc = customEvent.detail;
  docStore.onDocumentCreated(doc);
}

function handleDocDeleted(event: Event) {
  const customEvent = event as CustomEvent;
  const docId = customEvent.detail;
  docStore.onDocumentDeleted(docId);
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
