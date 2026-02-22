<template>
  <q-form ref="formRef" @submit="onSubmit" class="q-gutter-md">
    <ConfigurationGeneralFields v-model="localData" />

    <FileConfigFields
      v-model="localData.configuration"
      v-model:file="activeFile"
      :accept="localData.connector_type === 'local_file' ? '.csv' : undefined"
    />

    <q-select
      v-if="!props.hideAiProvider"
      v-model="localData.configuration.ai_provider"
      :options="aiProviderOptions"
      :label="$t('aiProvider')"
      color="white"
      standout
      emit-value
      map-options
      :disable="props.disableAiProvider"
    />

    <q-select
      v-if="!props.hideAcl"
      v-model="localData.configuration.connector_acl"
      :label="$t('connectorAcl')"
      use-input
      use-chips
      multiple
      input-debounce="0"
      @new-value="createValue"
      standout
      :hint="$t('connectorAclHint')"
      :rules="[
        (val: string[] | null | undefined) => (val && val.length > 0) || $t('aclTagRequired'),
      ]"
    >
      <template v-slot:selected-item="scope">
        <q-chip
          removable
          @remove="scope.removeAtIndex(scope.index)"
          :tabindex="scope.tabindex"
          color="accent"
          text-color="grey-3"
          size="md"
        >
          {{ scope.opt }}
        </q-chip>
      </template>
    </q-select>

    <q-select
      v-if="!props.hideSchedule"
      v-model="localData.schedule_type"
      :options="scheduleOptions"
      :label="$t('schedule')"
      dark
      color="white"
      standout
      emit-value
      map-options
      disable
      readonly
      hint="Manual upload only"
    />

    <div v-if="!props.hideActions" class="row justify-end q-gutter-sm q-mt-lg">
      <q-btn :label="$t('cancel')" flat text-color="grey-5" @click="onCancel" />
      <q-btn text-color="grey-3" color="accent" :label="$t('save')" type="submit" />
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import type { QForm } from 'quasar';
import { Connector } from 'src/models/Connector';
import { connectorService } from 'src/services/connectorService';
import ConfigurationGeneralFields from '../fields/ConfigurationGeneralFields.vue';
import FileConfigFields from '../fields/FileConfigFields.vue';

import { useQuasar } from 'quasar';
import { useNotification } from 'src/composables/useNotification';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

// --- DEFINITIONS ---
// The form modifies this data model directly via local copy
const data = defineModel<Connector>('data', { required: true });

// Emits 'save' to notify parent to persist changes
const emit = defineEmits(['save', 'cancel']);

const props = defineProps<{
  hideAiProvider?: boolean;
  disableAiProvider?: boolean;
  hideAcl?: boolean;
  hideSchedule?: boolean;
  hideActions?: boolean;
}>();

// --- STATE ---
// Form reference (optional, can be used for validation)
const formRef = ref<QForm | null>(null);

const scheduleOptions = computed(() => [
  { label: t('scheduleManual'), value: 'manual' },
  { label: t('scheduleDaily'), value: 'daily' },
  { label: t('scheduleWeekly'), value: 'weekly' },
  { label: t('scheduleMonthly'), value: 'monthly' },
]);

const aiProviderOptions = computed(() => [
  { label: t('gemini'), value: 'gemini' },
  { label: t('openai'), value: 'openai' },
  { label: t('local'), value: 'local' },
]);

// Local copy of data to avoid mutating prop directly until save
const localData = ref<Connector>(createCopy(data.value));

const activeFile = ref<File | null>(null);

// --- WATCHERS ---
watch(
  () => data.value,
  (newValue) => {
    // Compare JSON to avoid re-cloning if the prop update came from our own sync-back
    if (JSON.stringify(newValue) !== JSON.stringify(localData.value)) {
      localData.value = createCopy(newValue);
      activeFile.value = null; // Reset file input when data changes
    }
  },
  { deep: true },
);

// Sync changes back to parent immediately for dirty state detection
watch(
  [localData, activeFile],
  ([newLocalData]) => {
    Object.assign(data.value, newLocalData);
    data.value.configuration = { ...newLocalData.configuration };
  },
  { deep: true },
);

/**
 * Creates a deep copy of the KnowledgeBase object.
 * Ensures configuration object is cloned and recursive property is initialized.
 * Handles parsing of legacy string-based connector_acl.
 *
 * @param {Connector} source - The source connector to copy.
 * @returns {Connector} A specific deep copy of the connector.
 */
function createCopy(source: Connector): Connector {
  const copy = new Connector(source);
  copy.configuration = { ...source.configuration };

  if (!copy.configuration.ai_provider) {
    copy.configuration.ai_provider = 'gemini';
  }

  // Ensure connector_acl is an array if it exists
  let acl = copy.configuration.connector_acl;

  if (typeof acl === 'string' && acl.trim().startsWith('[') && acl.trim().endsWith(']')) {
    try {
      const parsed = JSON.parse(acl);
      if (Array.isArray(parsed)) {
        acl = parsed;
      }
    } catch {
      // ignore
    }
  }

  if (acl && !Array.isArray(acl)) {
    // Determine if it was a CSV string or just a single string?
    // Usually legacy was just a string. Let's wrap it.
    copy.configuration.connector_acl = [acl];
  } else if (!acl || acl.length === 0) {
    copy.configuration.connector_acl = ['public'];
  } else {
    // It is an array (original or parsed)
    copy.configuration.connector_acl = acl;
  }

  // Initialize recursive to false if undefined to prevent toggle glitch
  // FORCE MANUAL SCHEDULE FOR FILES
  copy.schedule_type = 'manual';
  return copy;
}

/**
 * Handles the creation of new values in the filtering ID select.
 *
 * @param {string} val - The value typed by the user.
 * @param {function} done - Callback to add the value.
 */
function createValue(val: string, done: (item: string, mode: 'add' | 'toggle') => void) {
  if (val.length > 0) {
    done(val, 'add');
  }
}

const $q = useQuasar();
const { notifyBackendError } = useNotification();

/**
 * Handles the form submission.
 * Uploads the file if one is selected, then updates the model and emits 'save'.
 */
async function onSubmit() {
  try {
    if (activeFile.value) {
      $q.loading.show({ message: 'Uploading file...' });
      const path = await connectorService.uploadFile(activeFile.value);
      localData.value.configuration.path = path;
      $q.loading.hide();
    } else {
      // Check if file is already uploaded
      if (localData.value.configuration.path) {
        // File already uploaded, proceed
      } else {
        // No file selected and none uploaded - check if other data changed
        const original = createCopy(data.value);
        if (JSON.stringify(localData.value) === JSON.stringify(original)) {
          // No changes at all, treat as cancel/close
          onCancel();
          return;
        }
      }
    }

    // Merge local changes back into the original data model
    Object.assign(data.value, localData.value);
    // Explicitly update configuration to ensure deep copy is merged
    data.value.configuration = { ...localData.value.configuration };

    // Notify parent to save the data
    emit('save');
    return true;
  } catch (error: unknown) {
    $q.loading.hide();
    notifyBackendError(error, t('failedToUploadFile', 'Failed to upload file'));
    return false;
  }
}

async function submit() {
  const valid = await formRef.value?.validate();
  if (!valid) return false;
  return await onSubmit();
}

/**
 * Cancels changes and resets the form to its initial state.
 */
function onCancel() {
  // Reset local data to match the original data (discard changes)
  localData.value = createCopy(data.value);
  activeFile.value = null;
  formRef.value?.resetValidation();
  // Note: Closing the drawer is handled by the parent or the drawer's overlay click
  emit('cancel');
}

defineExpose({ formData: localData, submit });
</script>
<style scoped>
.q-btn {
  border-radius: 8px !important;
}
</style>
