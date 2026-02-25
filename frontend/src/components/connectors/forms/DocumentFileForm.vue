<template>
  <q-form ref="formRef" @submit="onSubmit" class="q-gutter-md">
    <q-input
      v-model="localData.file_name"
      :label="$t('name')"
      color="white"
      standout
      lazy-rules="ondemand"
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-file
      v-model="activeFile"
      :display-value="activeFile ? undefined : localData.file_path"
      :accept="accept"
      clearable
      color="white"
      standout
      :label="$t('filePath')"
      lazy-rules="ondemand"
      :rules="[(val) => !!val || !!localData.file_path || $t('fieldRequired')]"
      @update:model-value="
        (val) => {
          if (val) {
            localData.file_path = val.name;
            // Auto-fill name if empty
            if (!localData.file_name) localData.file_name = val.name;
          } else localData.file_path = '';
        }
      "
    >
      <template v-slot:prepend>
        <q-icon name="attach_file" color="amber" />
      </template>
    </q-file>

    <div class="row justify-end q-gutter-sm q-mt-lg">
      <q-btn :label="$t('cancel')" flat text-color="grey-5" @click="onCancel" />
      <q-btn text-color="grey-3" color="accent" :label="$t('save')" type="submit" />
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar, type QForm } from 'quasar';
import { connectorService } from 'src/services/connectorService';
import { useNotification } from 'src/composables/useNotification';
import type { ConnectorDocument } from 'src/services/connectorDocumentService';

// --- DEFINITIONS ---
defineProps<{
  accept?: string;
}>();

// The form modifies this data model directly via local copy
const data = defineModel<Partial<ConnectorDocument>>('data', { required: true });

// Emits 'save' to notify parent to persist changes
const emit = defineEmits<{
  (e: 'save'): void;
  (e: 'cancel'): void;
}>();

// --- STATE ---
const $q = useQuasar();
const { t } = useI18n();
const { notify } = useNotification();

// Form reference (optional, can be used for validation)
const formRef = ref<QForm | null>(null);

// Local copy of data to avoid mutating prop directly until save
const localData = ref<Partial<ConnectorDocument>>(createCopy(data.value));

const activeFile = ref<File | null>(null);

// --- WATCHERS ---
watch(
  () => data.value,
  (newValue) => {
    localData.value = createCopy(newValue);
    activeFile.value = null; // Reset file input when data changes
  },
  { deep: true },
);

/**
 * Creates a valid copy of the data, ensuring configuration exists
 */
function createCopy(source: Partial<ConnectorDocument>): Partial<ConnectorDocument> {
  const copy = { ...source };
  copy.configuration = { ...source.configuration };
  return copy;
}

/**
 * Uploads the file if present, merges changes, and emits save event.
 */
async function onSubmit() {
  try {
    if (activeFile.value) {
      $q.loading.show({ message: t('uploadingFile', 'Uploading file...') });
      const path = await connectorService.uploadFile(activeFile.value);
      localData.value.file_path = path;
      localData.value.file_size = activeFile.value.size;
      $q.loading.hide();
    } else {
      // Check if data has changed
      const original = createCopy(data.value);
      if (JSON.stringify(localData.value) === JSON.stringify(original)) {
        onCancel();
        return;
      }
    }

    // Merge local changes back into the original data model
    Object.assign(data.value, localData.value);

    // Notify parent to save the data
    emit('save');
  } catch (error: unknown) {
    $q.loading.hide();
    const err = error as { response?: { data?: { code?: string; error_code?: string } } };

    console.log('DocumentFileForm error:', err.response?.data);

    // Check for CSV validation errors and reset the form
    if (
      err.response?.data?.code === 'csv_id_column_missing' ||
      err.response?.data?.code === 'csv_id_column_not_unique'
    ) {
      console.log('Resetting form due to CSV validation error');
      // Reset both localData and data to clear the form
      localData.value.file_name = '';
      localData.value.file_path = '';
      data.value.file_name = '';
      data.value.file_path = '';
      activeFile.value = null;
      formRef.value?.resetValidation();
      // Error will be displayed by global interceptor
      return;
    }

    // If handled by global interceptor, suppress local notification
    if (err.response?.data?.error_code) return;

    notify({
      type: 'negative',
      message: t('failedToUploadFile', 'Failed to upload file'),
      caption: error instanceof Error ? error.message : String(error),
    });
  }
}

/**
 * Resets the form and emits cancel event.
 */
function onCancel() {
  // Reset local data to match the original data (discard changes)
  localData.value = createCopy(data.value);
  activeFile.value = null;
  formRef.value?.resetValidation();
  emit('cancel');
}

defineExpose({ formData: localData });
</script>

<style scoped>
.q-btn {
  border-radius: 8px !important;
}
</style>
