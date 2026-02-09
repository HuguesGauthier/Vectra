<template>
  <q-form ref="formRef" @submit="onSubmit" class="q-gutter-md">
    <ConfigurationGeneralFields v-model="localData" />

    <q-select
      v-if="!hideAiProvider"
      v-model="localData.configuration.ai_provider"
      :options="aiProviderOptions"
      :label="$t('aiProvider')"
      dark
      color="white"
      standout
      emit-value
      map-options
      :disable="props.disableAiProvider"
    />

    <FolderConfigFields v-model="localData.configuration" />

    <q-select
      v-if="!props.hideAcl"
      v-model="connectorAcl"
      :label="$t('connectorAcl')"
      :hint="$t('connectorAclHint')"
      use-input
      use-chips
      multiple
      dark
      input-debounce="0"
      @new-value="createValue"
      standout
      :rules="[(val) => (val && val.length > 0) || $t('aclTagRequired')]"
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
    />

    <div v-if="!props.hideActions" class="row justify-end q-gutter-sm q-mt-lg">
      <q-btn :label="$t('cancel')" flat color="grey-5" @click="onCancel" />
      <q-btn
        text-color="grey-3"
        color="accent"
        :label="$t('save')"
        type="submit"
        :loading="props.loading"
      />
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Connector } from 'src/models/Connector';
import ConfigurationGeneralFields from '../fields/ConfigurationGeneralFields.vue';
import FolderConfigFields from '../fields/FolderConfigFields.vue';

const { t } = useI18n();

// --- DEFINITIONS ---
// The form modifies this data model directly via local copy
const data = defineModel<Connector>('data', { required: true });

// Emits 'save' to notify parent to persist changes
const emit = defineEmits(['save', 'cancel']);

const props = defineProps<{
  loading?: boolean;
  hideAiProvider?: boolean;
  disableAiProvider?: boolean;
  hideAcl?: boolean;
  hideSchedule?: boolean;
  hideActions?: boolean;
}>();

// --- STATE ---
const formRef = ref();

const scheduleOptions = computed(() => [
  { label: t('scheduleManual'), value: 'manual' },
  { label: t('schedule5m'), value: '5m' },
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

// --- COMPUTED ---
// Helper to map UI field to JSONB structure for connector-level ACL
const connectorAcl = computed({
  get: () => {
    const val = localData.value.configuration?.connector_acl;
    if (Array.isArray(val)) return val;
    // Fallback if it's a string or empty
    return val ? [val] : ['public'];
  },
  set: (val: string[] | null) => {
    if (!localData.value.configuration) localData.value.configuration = {};
    localData.value.configuration.connector_acl = val;
  },
});

// --- WATCHERS ---
watch(
  () => props.loading,
  (val) => {
    console.log('[FolderForm] loading prop changed:', val);
  },
);

watch(
  () => data.value,
  (newValue) => {
    localData.value = createCopy(newValue);
  },
  { deep: true },
);

// --- FUNCTIONS ---
/**
 * Creates a deep copy of the KnowledgeBase object.
 * Ensures configuration object is cloned and recursive property is initialized.
 */
function createCopy(source: Connector): Connector {
  const copy = new Connector(source);
  // Deep copy configuration to break reference
  copy.configuration = { ...source.configuration };
  // Initialize recursive to false if undefined to prevent toggle glitch
  if (copy.configuration.recursive === undefined) {
    copy.configuration.recursive = false;
  }
  if (!copy.configuration.ai_provider) {
    copy.configuration.ai_provider = 'gemini';
  }

  // Parse connector_acl if necessary (handle string JSON or CSV)
  let acl = copy.configuration.connector_acl;
  if (typeof acl === 'string' && acl.trim().startsWith('[') && acl.trim().endsWith(']')) {
    try {
      acl = JSON.parse(acl);
    } catch {
      // ignore
    }
  }

  if (Array.isArray(acl)) {
    copy.configuration.connector_acl = acl;
  } else if (acl) {
    copy.configuration.connector_acl = [acl as string];
  } else {
    // Default if missing
    copy.configuration.connector_acl = ['public'];
  }
  return copy;
}

function createValue(val: string, done: (item: string, mode: 'add' | 'toggle') => void) {
  if (val.length > 0) {
    done(val, 'add');
  }
}

function onSubmit() {
  // Merge local changes back into the original data model
  Object.assign(data.value, localData.value);
  // Explicitly update configuration to ensure deep copy is merged
  data.value.configuration = { ...localData.value.configuration };

  // Notify parent to save the data
  emit('save');
}

async function submit() {
  const valid = await formRef.value?.validate();
  if (!valid) return false;
  onSubmit();
  return true;
}

function onCancel() {
  // Reset local data to match the original data (discard changes)
  localData.value = createCopy(data.value);
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
