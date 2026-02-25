<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Search / Filter Bar & Add Button -->
    <div class="row q-mb-xl items-center q-gutter-x-md">
      <q-input
        v-model="filter"
        filled
        dense
        class="search-input col-12 col-md-4"
        :placeholder="$t('search')"
        clearable
        style="max-width: 375px"
      >
        <template #prepend>
          <q-icon name="search" />
        </template>
      </q-input>

      <q-btn color="accent" icon="add" size="14px" round unelevated @click="openTypeSelection">
        <AppTooltip>{{ $t('createNew') }}</AppTooltip>
      </q-btn>
    </div>

    <!-- Loading State -->
    <div v-if="connectorStore.loading" class="row justify-center q-pa-xl">
      <q-spinner-dots size="50px" color="accent" />
    </div>

    <!-- Empty State -->
    <div v-else-if="sortedConnectors.length === 0" class="column flex-center text-center q-pa-xl">
      <q-icon name="library_add" size="100px" color="grey-7" class="q-mb-md" />
      <div class="text-h5 text-grey-5 q-mb-xs">{{ $t('noConnectorsFound') }}</div>
      <div class="text-subtitle2 text-grey-7 q-mb-lg">
        {{ $t('addFirstSource') }}
      </div>
      <q-btn
        color="accent"
        :label="$t('createNew')"
        icon="add"
        padding="10px 24px"
        rounded
        unelevated
        @click="openTypeSelection"
      />
    </div>

    <!-- Connectors Card Grid -->
    <div v-else class="row q-col-gutter-lg">
      <div 
        v-for="connector in filteredConnectors" 
        :key="connector.id" 
        class="col-12 col-sm-6 col-md-4 col-xl-3"
      >
        <ConnectorManagementCard
          :connector="connector"
          @edit="openDrawerViaDataSource(connector)"
          @delete="confirmDelete(connector)"
          @sync="syncSource(connector)"
          @refresh="refreshFiles(connector)"
          @view-docs="openDocumentsDialog(connector)"
          @toggle="(val) => toggleSource(connector, val)"
          @show-error="showError(connector)"
        />
      </div>
    </div>

    <ConnectorStepper
      v-model:isOpen="isStepperOpen"
      :loading="isSaving"
      :is-edit="isEditMode"
      :initial-data="theConnectors.editingConnector"
      @save="onConnectorSaved"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import { Connector, type ConnectorSavePayload } from 'src/models/Connector';
import { ConnectorStatus, ConnectorType } from 'src/models/enums';
import ConnectorStepper from 'src/components/connectors/ConnectorStepper.vue';
import ConnectorManagementCard from 'src/components/connectors/ConnectorManagementCard.vue';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import { useConnectorStore } from 'src/stores/ConnectorStore';
import { useConnectorActions } from 'src/composables/useConnectorActions';

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
  selected: null as Connector | null,
  editingConnector: null as Connector | null,
});

const isStepperOpen = ref(false);
const isEditMode = ref(false);
const selectedType = ref<string>('');
const filter = ref('');

// --- COMPUTED ---

/**
 * All connectors sorted by provider, then type, then name
 */
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
 * Filtered connectors based on search input
 */
const filteredConnectors = computed(() => {
  if (!filter.value) return sortedConnectors.value;
  const search = filter.value.toLowerCase();
  return sortedConnectors.value.filter((c) => {
    // 1. Name & Description
    if (c.name.toLowerCase().includes(search)) return true;
    if (c.description?.toLowerCase().includes(search)) return true;

    // 2. Type & Provider
    if (c.connector_type.toLowerCase().includes(search)) return true;
    const provider = c.configuration?.ai_provider || 'gemini';
    if (provider.toLowerCase().includes(search)) return true;
    if (t(provider.toLowerCase()).toLowerCase().includes(search)) return true;

    // 3. Status & Error
    if (c.status.toLowerCase().includes(search)) return true;
    if (t(c.status).toLowerCase().includes(search)) return true;
    if (c.last_error?.toLowerCase().includes(search)) return true;

    // 4. ACL Tags
    const aclTags = c.configuration?.connector_acl || [];
    if (aclTags.some((tag: string) => tag.toLowerCase().includes(search))) return true;

    return false;
  });
});

// --- LIFECYCLE ---

onMounted(async () => {
  if (connectorStore.connectors.length === 0) {
    await connectorStore.fetchAll();
  }
});

// --- FUNCTIONS ---

function mapBackendToUiType(connector: Connector): string {
  if (connector.connector_type === ConnectorType.LOCAL_FOLDER) return 'folder';
  if (connector.connector_type === ConnectorType.LOCAL_FILE) return 'file';
  return connector.connector_type;
}

/**
 * Opens the drawer to edit an existing data source.
 */
function openDrawerViaDataSource(source: Connector) {
  selectedType.value = mapBackendToUiType(source);
  theConnectors.selected = source;
  theConnectors.editingConnector = new Connector(source);
  if (source.configuration) {
    theConnectors.editingConnector.configuration = JSON.parse(JSON.stringify(source.configuration));
  }
  isEditMode.value = true;
  isStepperOpen.value = true;
}

/**
 * Opens the documents page for a specific connector.
 */
function openDocumentsDialog(source: Connector) {
  void router.push({ name: 'ConnectorDocuments', params: { id: source.id } });
}

/**
 * Opens the type selection dialog for creating a new connector.
 */
function openTypeSelection() {
  theConnectors.selected = null;
  theConnectors.editingConnector = null;
  selectedType.value = '';
  isEditMode.value = false;
  isStepperOpen.value = true;
}

/**
 * Handles the save event from the connector drawer.
 */
async function onConnectorSaved(payload: ConnectorSavePayload) {
  await handleSaveConnector(payload, theConnectors.selected, () => {
    isStepperOpen.value = false;
  });
}

/**
 * Confirms and executes the deletion of a connector.
 */
function confirmDelete(connector: Connector) {
  handleDeleteConnector(connector);
}

/**
 * Toggles the enabled state of a source.
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
 * Displays the error message for a failed connector.
 */
function showError(source: Connector) {
  if (source.status === ConnectorStatus.ERROR && source.last_error) {
    notify({
      type: 'negative',
      message: source.last_error,
      timeout: 0,
      actions: [{ label: t('dismiss'), color: 'white', handler: () => {} }],
    });
  }
}

/**
 * Triggers a manual file scan/refresh for a folder connector.
 */
function refreshFiles(source: Connector) {
  void handleScanFiles(source);
}
</script>

<style scoped>
.search-input :deep(.q-field__control) {
  border-radius: 12px;
  background: var(--q-primary) !important;
  border: 1px solid var(--q-third);
}

.search-input :deep(.q-field__control:before),
.search-input :deep(.q-field__control:after) {
  display: none !important;
}
</style>
