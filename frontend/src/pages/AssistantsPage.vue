<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Title Header -->
    <div class="row items-center justify-between q-pt-md q-pb-md q-pl-none q-mb-md">
      <div>
        <div class="text-h4 text-weight-bold">{{ $t('myAssistants') }}</div>
        <div class="text-subtitle1 q-pt-xs">
          {{ $t('myAssistantsDesc') }}
        </div>
      </div>
    </div>

    <div class="column q-gutter-y-md">
      <!-- Assistants Table -->
      <div>
        <AppTable
          :rows="theAssistants.list"
          :columns="columns"
          :loading="loading"
          v-model:filter="filter"
          :no-data-title="$t('noAssistants')"
          :no-data-message="$t('createYourFirstAssistant')"
          no-data-icon="psychology"
        >
          <!-- Add Button Slot -->
          <template #add-button>
            <q-btn color="accent" icon="add" size="12px" round unelevated @click="openCreateDrawer">
              <AppTooltip>{{ $t('createNew') }}</AppTooltip>
            </q-btn>
          </template>

          <!-- No Data Action Slot -->
          <template #no-data-action>
            <q-btn
              color="accent"
              size="12px"
              icon="add"
              round
              unelevated
              @click="openCreateDrawer"
            />
          </template>

          <!-- Body Slot for Custom Cells -->
          <template #body="{ props }">
            <q-tr :props="props">
              <!-- Avatar Column -->
              <q-td key="avatar" :props="props">
                <q-avatar
                  size="sm"
                  :color="
                    !props.row.avatar_image &&
                    props.row.avatar_bg_color &&
                    !props.row.avatar_bg_color.startsWith('#') &&
                    !props.row.avatar_bg_color.startsWith('rgb')
                      ? props.row.avatar_bg_color
                      : undefined
                  "
                  :style="
                    !props.row.avatar_image &&
                    props.row.avatar_bg_color &&
                    (props.row.avatar_bg_color.startsWith('#') ||
                      props.row.avatar_bg_color.startsWith('rgb'))
                      ? { backgroundColor: props.row.avatar_bg_color }
                      : {}
                  "
                  :text-color="props.row.avatar_text_color || 'white'"
                >
                  <img
                    v-if="props.row.avatar_image"
                    :src="`${assistantService.getAvatarUrl(props.row.id)}?t=${theAssistants.avatarRefreshKey}`"
                    style="object-fit: cover"
                    :style="{
                      objectPosition: `center ${props.row.avatar_vertical_position ?? 50}%`,
                    }"
                  />
                  <q-icon v-else name="psychology" />
                </q-avatar>
              </q-td>

              <!-- Name Column -->
              <q-td key="name" :props="props">
                <div
                  class="text-weight-bold cursor-pointer hover-underline"
                  @click="openEditDrawer(props.row)"
                >
                  {{ props.row.name }}
                </div>
              </q-td>

              <!-- Description Column -->
              <q-td key="description" :props="props" style="max-width: 300px">
                <div class="ellipsis">{{ props.row.description }}</div>
                <AppTooltip v-if="props.row.description && props.row.description.length > 50">
                  {{ props.row.description }}
                </AppTooltip>
              </q-td>

              <!-- Model Column -->
              <q-td key="model" :props="props">
                {{ getChatProviderLabel(props.row.model) }}
              </q-td>

              <!-- Data Sources Column -->
              <q-td key="data_sources" :props="props">
                <div class="row q-gutter-xs">
                  <template v-if="getAssistantConnectors(props.row).length > 0">
                    <q-chip
                      v-for="source in getAssistantConnectors(props.row).slice(0, 2)"
                      :key="source.id"
                      size="xs"
                      color="accent"
                      text-color="grey-3"
                      class="q-ma-none q-mt-xs q-mr-xs"
                    >
                      {{ source.name }}
                    </q-chip>
                    <q-chip
                      v-if="getAssistantConnectors(props.row).length > 2"
                      size="xs"
                      color="accent"
                      text-color="grey-3"
                      class="q-ma-none q-mt-xs q-mr-xs"
                    >
                      +{{ getAssistantConnectors(props.row).length - 2 }}
                    </q-chip>
                  </template>
                  <span v-else class="text-grey-7">—</span>
                </div>
              </q-td>

              <!-- ACL Column -->
              <q-td key="acl" :props="props">
                <div class="row q-gutter-xs">
                  <template v-if="(props.row.configuration?.tags?.length || 0) > 0">
                    <q-chip
                      v-for="tag in props.row.configuration?.tags"
                      :key="tag"
                      size="xs"
                      color="accent"
                      text-color="grey-3"
                      class="q-ma-none q-mt-xs q-mr-xs"
                    >
                      {{ tag }}
                    </q-chip>
                  </template>
                  <span v-else class="text-grey-7">—</span>
                </div>
              </q-td>

              <!-- Actions Column -->
              <q-td key="actions" :props="props">
                <div class="row items-center q-gutter-x-sm">
                  <q-btn round flat dense size="sm" icon="chat" @click="openPublicChat(props.row)">
                    <AppTooltip>{{ $t('talk') }}</AppTooltip>
                  </q-btn>
                  <q-btn round flat dense size="sm" icon="share" @click="copyJoinLink(props.row)">
                    <AppTooltip>{{ $t('share') }}</AppTooltip>
                  </q-btn>
                  <q-btn round flat dense size="sm" icon="edit" @click="openEditDrawer(props.row)">
                    <AppTooltip>{{ $t('edit') }}</AppTooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    dense
                    size="sm"
                    icon="delete_sweep"
                    color="warning"
                    @click="confirmPurgeCache(props.row)"
                  >
                    <AppTooltip>{{ $t('performance.purgeCache') }}</AppTooltip>
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
    </div>

    <!-- Drawer -->
    <AssistantDrawer
      v-model="isDrawerOpen"
      :assistant-to-edit="editingAssistant"
      @save="handleSave"
    />

    <!-- Create Stepper -->
    <AddAssistantStepper
      v-model:isOpen="isStepperOpen"
      :loading="loading"
      @save="(data, file) => handleStepperSave(data, file)"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { type QTableColumn, Notify } from 'quasar';
import { useNotification } from 'src/composables/useNotification';
import { assistantService, type Assistant } from 'src/services/assistantService';
import { connectorService, type Connector } from 'src/services/connectorService';
import AddAssistantStepper from 'components/assistants/AddAssistantStepper.vue';
import AssistantDrawer from 'components/assistants/AssistantDrawer.vue';
import AppTooltip from 'components/common/AppTooltip.vue';
import AppTable from 'components/common/AppTable.vue';
import { useDialog } from 'src/composables/useDialog';
import { useAiProviders } from 'src/composables/useAiProviders';

// --- DEFINITIONS ---
defineOptions({
  name: 'AssistantsPage',
});

// Force HMR update

// --- STATE ---
const { t } = useI18n();
const router = useRouter();
const { confirm } = useDialog();
const { notifySuccess } = useNotification();
const { getChatProviderLabel } = useAiProviders();
// const store = useAssistantStore(); // This line was in the instruction but not in the original code, and no context for useAssistantStore. Keeping original structure.

const theAssistants = reactive({
  list: [] as Assistant[],
  selected: null as Assistant | null,
  refreshTimer: null as ReturnType<typeof setInterval> | null,
  avatarRefreshKey: Date.now(),
});

const connectors = ref<Connector[]>([]);
const loading = ref(true);
const filter = ref('');

// Drawer & Stepper state
const isDrawerOpen = ref(false); // For edits
const isStepperOpen = ref(false); // For creation
const editingAssistant = ref<Assistant | null>(null);

// --- COMPUTED ---

/**
 * Table columns definition
 */
const columns = computed<QTableColumn[]>(() => [
  {
    name: 'avatar',
    required: true,
    label: '',
    align: 'center',
    field: (row: Assistant) => row.avatar_bg_color,
    sortable: false,
  },
  {
    name: 'name',
    required: true,
    label: t('name'),
    align: 'left',
    field: (row: Assistant) => row.name,
    sortable: true,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'description',
    align: 'left',
    label: t('description'),
    field: (row: Assistant) => row.description,
    sortable: true,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'model',
    align: 'left',
    label: t('chatEngine'),
    field: (row: Assistant) => getChatProviderLabel(row.model),
    sortable: true,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'data_sources',
    align: 'left',
    label: t('dataSources'),
    field: (row: Assistant) => getAssistantConnectors(row).length,
    sortable: true,
    style: 'color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'acl',
    align: 'left',
    label: t('acl'),
    field: (row: Assistant) => row.configuration?.tags,
    sortable: false,
    style: 'max-width: 200px;color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
  {
    name: 'actions',
    align: 'left',
    label: '',
    field: 'actions',
    sortable: false,
    style: 'width: 200px;color: var(--q-text-main)',
    headerStyle: 'color: var(--q-text-main)',
  },
]);

// --- LIFECYCLE ---
onMounted(async () => {
  await loadData();
});

// --- FUNCTIONS ---

/**
 * Loads all assistants and connectors from the backend.
 */
async function loadData() {
  loading.value = true;
  try {
    const [assistantsData, connectorsData] = await Promise.all([
      assistantService.getAll(),
      connectorService.getAll(),
    ]);
    theAssistants.list = assistantsData;
    connectors.value = connectorsData;
  } finally {
    loading.value = false;
  }
}

/**
 * Helper to get the list of connectors for an assistant.
 * Uses linked_connectors object if available, otherwise maps IDs to names.
 */
function getAssistantConnectors(assistant: Assistant): { id: string; name: string }[] {
  if (assistant.linked_connectors && assistant.linked_connectors.length > 0) {
    return assistant.linked_connectors;
  }

  if (assistant.linked_connector_ids && assistant.linked_connector_ids.length > 0) {
    return assistant.linked_connector_ids
      .map((id) => {
        const conn = connectors.value.find((c) => c.id === id);
        return conn ? { id: conn.id, name: conn.name } : null;
      })
      .filter((c): c is { id: string; name: string } => c !== null);
  }

  return [];
}

/**
 * Opens stepper to create a new assistant.
 */
function openCreateDrawer() {
  editingAssistant.value = null;
  isStepperOpen.value = true;
}

/**
 * Opens drawer to edit an existing assistant.
 * @param {Assistant} assistant - The assistant to edit.
 */
function openEditDrawer(assistant: Assistant) {
  editingAssistant.value = assistant;
  isDrawerOpen.value = true;
}

/**
 * Handles the save event from the drawer (Edit Mode).
 */
async function handleSave(data: Partial<Assistant>) {
  if (editingAssistant.value) {
    await assistantService.update(editingAssistant.value.id, data);
    notifySuccess(t('assistantUpdated'));
    isDrawerOpen.value = false;
    theAssistants.avatarRefreshKey = Date.now(); // Force avatar refresh
    await loadData();
  }
}

/**
 * Handles the save event from the stepper (Create Mode).
 */
/**
 * Handles the save event from the stepper (Create Mode).
 */
async function handleStepperSave(data: Partial<Assistant>, avatarFile?: File | null) {
  const newAssistant = await assistantService.create(data);

  // Handle avatar upload if provided
  if (avatarFile) {
    try {
      await assistantService.uploadAvatar(newAssistant.id, avatarFile);
    } catch {
      // Notify warning but don't fail the whole creation flow visually
      notifySuccess(
        t('assistantCreatedButAvatarFailed') || 'Assistant created but avatar upload failed',
      );
      // But we still refresh data so continue
    }
  }

  notifySuccess(t('assistantCreated'));
  isStepperOpen.value = false;
  theAssistants.avatarRefreshKey = Date.now(); // Force avatar refresh
  await loadData();
}

/**
 * Opens a dialog to confirm deletion of an assistant.
 * @param {Assistant} assistant - The assistant to delete.
 */
function confirmDelete(assistant: Assistant) {
  confirm({
    title: t('confirmDeletion'),
    message: t('confirmDeletionMessage', { name: assistant.name }),
    confirmLabel: t('delete'),
    confirmColor: 'negative',
    onConfirm: () => {
      void (async () => {
        loading.value = true;
        try {
          await assistantService.delete(assistant.id);
          notifySuccess(t('assistantDeleted'));
        } catch (error) {
          console.error('Failed to delete assistant:', error);
          Notify.create({
            type: 'negative',
            message: t('errors.ASSISTANT_DELETION_FAILED') || 'Failed to delete assistant',
            position: 'bottom-right',
          });
        } finally {
          // Always reload the list to reflect current state
          await loadData();
        }
      })();
    },
  });
}

/**
 * Copies the public share link to the clipboard.
 * @param {Assistant} assistant - The assistant to share.
 */
function copyJoinLink(assistant: Assistant) {
  const routeLocation = router.resolve({ path: `/share/${assistant.id}` });
  const url = new URL(routeLocation.href, window.location.origin).href;

  void navigator.clipboard.writeText(url);
  notifySuccess(t('linkCopied'));
}

/**
 * Opens the public chat in a new tab.
 * @param {Assistant} assistant - The assistant to chat with.
 */
function openPublicChat(assistant: Assistant) {
  const routeLocation = router.resolve({ path: `/share/${assistant.id}` });
  const url = new URL(routeLocation.href, window.location.origin).href;
  window.open(url, '_blank');
}

/**
 * Opens a dialog to confirm purging the assistant's cache.
 * @param {Assistant} assistant - The assistant to purge cache for.
 */
function confirmPurgeCache(assistant: Assistant) {
  confirm({
    title: t('performance.purgeConfirmTitle'),
    message: t('performance.purgeConfirmMessage'),
    confirmLabel: t('performance.purgeCache'),
    confirmColor: 'negative',
    onConfirm: () => {
      void (async () => {
        try {
          const result = await assistantService.clearCache(assistant.id);
          notifySuccess(`${t('performance.purgeSuccess')} (${result.deleted_count} items)`);
        } catch (error) {
          console.error(error);
          Notify.create({
            type: 'negative',
            message: t('performance.purgeFailed') || 'Failed to purge cache',
          });
        }
      })();
    },
  });
}
</script>

<style scoped>
.hover-underline:hover {
  text-decoration: underline;
}
</style>
