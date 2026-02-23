<template>
  <q-page class="bg-primary q-pa-lg">

    <!-- Search / Filter Bar -->
    <div class="row q-mb-lg items-center q-gutter-x-md">
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

      <!-- Add Button -->
      <q-btn color="accent" icon="add" size="14px" round unelevated @click="openCreateDrawer">
        <AppTooltip>{{ $t('createNew') }}</AppTooltip>
      </q-btn>
    </div>

    <!-- Grid Layout -->
    <div v-if="loading" class="row q-col-gutter-lg">
      <div v-for="i in 6" :key="i" class="col-12 col-sm-6 col-md-4 col-lg-3">
        <q-skeleton type="rect" height="350px" style="border-radius: 24px" />
      </div>
    </div>

    <div v-else-if="filteredAssistants.length > 0" class="row q-col-gutter-lg">
      <div
        v-for="assistant in filteredAssistants"
        :key="assistant.id"
        class="col-12 col-sm-6 col-md-4 col-lg-3"
      >
        <AssistantManagementCard
          :assistant="assistant"
          :connectors="getAssistantConnectors(assistant)"
          :refresh-key="theAssistants.avatarRefreshKey"
          @edit="openEditDrawer(assistant)"
          @delete="confirmDelete(assistant)"
          @share="copyJoinLink(assistant)"
          @chat="openPublicChat(assistant)"
          @purge="confirmPurgeCache(assistant)"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="column flex-center q-pa-xl empty-state">
      <q-icon name="psychology" size="80px" color="grey-8" class="q-mb-md" />
      <div class="text-h5 text-weight-bold text-grey-6">{{ $t('noAssistants') }}</div>
      <div class="text-subtitle1 text-grey-8 q-mb-lg text-center">
        {{ $t('createYourFirstAssistant') }}
      </div>
      <q-btn
        color="accent"
        :label="$t('createNew')"
        icon="add"
        padding="10px 24px"
        rounded
        unelevated
        @click="openCreateDrawer"
      />
    </div>

    <!-- Unified Stepper (Create & Edit) -->
    <AssistantStepper
      v-model:isOpen="isStepperOpen"
      :assistant-to-edit="editingAssistant"
      :loading="saving"
      @save="handleStepperSave"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { Notify } from 'quasar';
import { useNotification } from 'src/composables/useNotification';
import { assistantService, type Assistant } from 'src/services/assistantService';
import { connectorService, type Connector } from 'src/services/connectorService';
import AssistantManagementCard from 'src/components/assistants/AssistantManagementCard.vue';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import { useDialog } from 'src/composables/useDialog';

const AssistantStepper = defineAsyncComponent(
  () => import('src/components/assistants/AssistantStepper.vue'),
);

// --- DEFINITIONS ---
defineOptions({
  name: 'AssistantsPage',
});

// --- STATE ---
const { t } = useI18n();
const router = useRouter();
const { confirm } = useDialog();
const { notifySuccess } = useNotification();

const theAssistants = reactive({
  list: [] as Assistant[],
  avatarRefreshKey: Date.now(),
});

const connectors = ref<Connector[]>([]);
const loading = ref(true);
const filter = ref('');

// Stepper state
const isStepperOpen = ref(false); // For both Create & Edit
const editingAssistant = ref<Assistant | null>(null);
const saving = ref(false); // separate loading state for save operations

// --- COMPUTED ---

/**
 * Filtered list of assistants based on search string
 */
const filteredAssistants = computed(() => {
  if (!filter.value) return theAssistants.list;
  const search = filter.value.toLowerCase();
  return theAssistants.list.filter((a) => {
    // 1. Name & Description
    if (a.name.toLowerCase().includes(search)) return true;
    if (a.description?.toLowerCase().includes(search)) return true;

    // 2. Model & Provider
    if (a.model?.toLowerCase().includes(search)) return true;
    if (a.model_provider?.toLowerCase().includes(search)) return true;
    // Special display case for Ollama/Mistral
    if (a.model_provider?.toLowerCase() === 'ollama' && 'mistral'.includes(search)) return true;

    // 3. Tags (ACL)
    const tags = a.configuration?.tags || [];
    if (tags.some((t) => t.toLowerCase().includes(search))) return true;

    // 4. Linked Connectors
    const linked = getAssistantConnectors(a);
    if (linked.some((c) => c.name.toLowerCase().includes(search))) return true;

    return false;
  });
});

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
  } catch (e) {
    console.error(e);
    Notify.create({
      type: 'negative',
      message: t('errors.loading_failed') || 'Failed to load assistants',
    });
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
  isStepperOpen.value = true;
}

/**
 * Handles the save event from the stepper (Create & Edit Mode).
 */
async function handleStepperSave(data: Partial<Assistant>, avatarFile?: File | null) {
  saving.value = true;
  try {
    // If we have an ID, it's an update
    if (data.id) {
      await assistantService.update(data.id, data);
      // If avatar file provided during edit
      if (avatarFile) {
        try {
          await assistantService.uploadAvatar(data.id, avatarFile);
        } catch {
          notifySuccess(t('assistantUpdatedButAvatarFailed'));
        }
      }
      notifySuccess(t('assistantUpdated'));
    }
    // Otherwise it's a creation
    else {
      const newAssistant = await assistantService.create(data);

      // Handle avatar upload if provided
      if (avatarFile) {
        try {
          await assistantService.uploadAvatar(newAssistant.id, avatarFile);
        } catch {
          notifySuccess(t('assistantCreatedButAvatarFailed'));
        }
      }
      notifySuccess(t('assistantCreated'));
    }

    isStepperOpen.value = false;
    theAssistants.avatarRefreshKey = Date.now();
    await loadData();
  } catch (error) {
    console.error(error);
    Notify.create({
      type: 'negative',
      message: t('errors.saving_failed') || 'Failed to save assistant',
    });
  } finally {
    saving.value = false;
  }
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

.search-input :deep(.q-field__control) {
  border-radius: 12px;
  background: var(--q-primary) !important;
  border: 1px solid var(--q-third);
}

.search-input :deep(.q-field__control:before),
.search-input :deep(.q-field__control:after) {
  display: none !important;
}

.empty-state {
  margin-top: 100px;
  opacity: 0.8;
}
</style>
