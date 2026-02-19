<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card class="bg-primary column full-height" style="min-width: 55vw">
      <!-- Header -->
      <div class="q-pa-md bg-primary border-bottom row items-center justify-between">
        <div class="text-h6 text-weight-bold">
          {{
            isEdit
              ? $t('editConnector', { type: connectorData.name })
              : $t('addConnector', { type: '' }).replace('  ', ' ')
          }}
        </div>
        <q-btn flat round dense icon="close" @click="handleClose" />
      </div>

      <!-- Stepper Header -->
      <div class="bg-primary q-px-sm">
        <q-stepper
          v-model="step"
          ref="stepper"
          color="accent"
          active-color="accent"
          done-color="positive"
          alternative-labels
          animated
          flat
          dense
          class="bg-transparent"
          :header-nav="isEdit"
        >
          <q-step
            :name="1"
            :title="$t('selectType')"
            icon="settings_input_component"
            :done="step > 1"
          />
          <q-step :name="2" :title="$t('configure')" icon="tune" :done="step > 2" />
          <q-step
            :name="3"
            :title="$t('selectVectorizationEngine')"
            icon="psychology"
            :done="step > 3"
          />
          <q-step :name="4" :title="$t('schedule')" icon="event" :done="step > 4" />
          <q-step :name="5" :title="$t('acl')" icon="lock" :done="step > 5" />
        </q-stepper>
      </div>

      <!-- Content Area -->
      <div class="col scroll q-pl-lg q-pr-lg relative-position bg-primary hide-scrollbar">
        <!-- Step 1: Connector Type Selection -->
        <ConnectorTypeStep v-if="step === 1 && !isEdit" v-model="selectedType" />
        <div v-else-if="step === 1 && isEdit" class="q-pa-md text-center">
          <div class="text-h6">Type: {{ selectedType }}</div>
          <div class="text-subtitle2 text-grey-6">Cannot change type during edit.</div>
        </div>

        <!-- Step 2: Specific Configuration (Moved from Step 3) -->
        <div v-if="step === 2" class="row justify-center">
          <div class="col-12 col-lg-10">
            <component
              :is="currentForm"
              ref="activeForm"
              :data="connectorData"
              hide-ai-provider
              hide-acl
              hide-schedule
              hide-actions
              :loading="loading"
              :is-edit="isEdit"
              @cancel="step = 1"
            />
          </div>
        </div>

        <!-- Step 3: Vectorization Engine (REFACTORED: Vertical Stepper) -->
        <div v-if="step === 3" class="max-width-container">
          <q-stepper
            v-model="subStep"
            vertical
            color="accent"
            active-color="accent"
            done-color="accent"
            animated
            flat
            class="bg-transparent"
          >
            <!-- Sub-Step 1: Select Engine -->
            <q-step
              :name="1"
              :title="$t('selectVectorizationEngine')"
              icon="settings_input_component"
              :done="subStep > 1"
            >
              <ProviderSelection
                v-model="selectedProvider"
                :providers="aiProviders"
                :selectable="true"
                class="full-width"
                show-config-button
                :config-label="$t('configure')"
                @configure="showAdvancedSettings = true"
              />
            </q-step>

            <!-- Sub-Step 2: Smart Extraction -->
            <q-step
              :name="2"
              :title="$t('smartExtractionTitle')"
              icon="psychology"
              :done="subStep > 2"
            >
              <SmartExtractionConfig v-model="smartExtractionEnabled" />
            </q-step>
          </q-stepper>

          <!-- Advanced Settings Dialog -->
          <AdvancedIndexingSettings
            v-model:isOpen="showAdvancedSettings"
            :chunk-size="connectorData.configuration?.chunk_size"
            :chunk-overlap="connectorData.configuration?.chunk_overlap"
            @update="handleAdvancedSettingsUpdate"
          />
        </div>

        <!-- Step 4: Schedule (Moved from Step 5) -->
        <div v-if="step === 4" class="row justify-center max-width-container">
          <div class="col-12 text-center q-mb-lg">
            <div class="text-h4 text-weight-bold text-white q-mb-sm">
              {{ $t('syncSchedule') }}
            </div>
            <div class="text-subtitle1 text-grey-6">{{ $t('syncScheduleDesc') }}</div>
          </div>

          <ScheduleOptions v-model="connectorData.schedule_cron" :connector-type="selectedType" />
        </div>

        <!-- Step 5: Access Control (Moved from Step 4) -->
        <div v-if="step === 5" class="row justify-center max-width-container">
          <div class="col-12 text-center q-mb-lg">
            <div class="text-h4 text-weight-bold text-white q-mb-sm">
              {{ $t('accessControl') }}
            </div>
            <div class="text-subtitle1 text-grey-6">{{ $t('accessControlDesc') }}</div>
          </div>

          <!-- ACL Mode Selection -->
          <div class="col-12 row q-col-gutter-md justify-center q-mb-xl">
            <div v-for="mode in aclModes" :key="mode.id" class="col-12 col-sm-5">
              <q-card
                class="selection-card cursor-pointer full-height q-pa-md"
                :class="{ selected: aclMode === mode.id }"
                v-ripple
                @click="aclMode = mode.id"
              >
                <q-card-section class="column items-center text-center">
                  <q-icon :name="mode.icon" size="48px" class="q-mb-md" :color="mode.color" />
                  <div class="text-h6 text-white">{{ mode.name }}</div>
                  <div class="text-caption text-grey-5 q-mt-sm">{{ mode.description }}</div>
                </q-card-section>
                <div v-if="aclMode === mode.id" class="selected-overlay">
                  <q-icon name="check_circle" color="accent" size="32px" />
                </div>
              </q-card>
            </div>
          </div>

          <!-- Tag Input for Restricted Mode -->
          <div v-if="aclMode === 'restricted'" class="col-12 col-md-8">
            <q-card class="bg-secondary q-pa-md border-light">
              <div class="text-subtitle1 text-white q-mb-sm">{{ $t('defineAccessTags') }}</div>
              <q-select
                v-model="connectorData.configuration.connector_acl"
                :label="$t('connectorAcl')"
                :hint="$t('connectorAclHint')"
                use-input
                use-chips
                multiple
                dark
                standout
                input-debounce="0"
                @new-value="createValue"
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
            </q-card>
          </div>
        </div>
      </div>
      <div class="q-pa-md bg-primary border-top row justify-between items-center">
        <q-btn
          v-if="step > 1"
          flat
          color="grey-5"
          :label="$t('back')"
          icon="arrow_back"
          @click="handleBack"
        />
        <div v-else></div>
        <!-- Spacer -->

        <div v-if="step < 5" class="row items-center q-gutter-sm">
          <q-btn
            v-if="
              step === 2 &&
              (selectedType === 'sql' || selectedType === 'vanna_sql') &&
              activeForm?.step === 2
            "
            outline
            color="accent"
            :label="$t('testConnection')"
            :loading="activeForm.isTesting"
            class="q-mr-sm"
            @click="activeForm.onTestConnection?.()"
          />

          <template v-if="isEdit">
            <q-btn :label="$t('cancel')" flat color="grey-5" @click="handleClose" />
            <q-btn color="accent" :label="$t('save')" :loading="loading" @click="handleSave" />
          </template>

          <q-btn
            color="accent"
            :label="$t('next')"
            icon-right="arrow_forward"
            :disable="isNextDisabled"
            @click="handleNext"
          />
        </div>
        <div v-else class="row items-center q-gutter-sm">
          <template v-if="isEdit">
            <q-btn :label="$t('cancel')" flat color="grey-5" @click="handleClose" />
          </template>
          <q-btn color="accent" :label="$t('save')" :loading="loading" @click="handleSave" />
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, type Component, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Connector } from 'src/models/Connector';
import { ConnectorType, ScheduleType } from 'src/models/enums';
import FolderForm from './forms/FolderForm.vue';
import SqlForm from './forms/SqlForm.vue';
import ConnectorFileForm from './forms/ConnectorFileForm.vue';
import SmartExtractionConfig from './fields/SmartExtractionConfig.vue';
import AdvancedIndexingSettings from './dialogs/AdvancedIndexingSettings.vue';
import { useDialog } from 'src/composables/useDialog';
import { connectorService } from 'src/services/connectorService';
// import AppTooltip from 'src/components/common/AppTooltip.vue';
import ConnectorTypeStep from './ConnectorTypeStep.vue';
import { settingsService } from 'src/services/settingsService';
import ScheduleOptions from './ScheduleOptions.vue';
import ProviderSelection from 'src/components/common/ProviderSelection.vue';
import { useAiProviders } from 'src/composables/useAiProviders';

// --- DEFINITIONS ---
defineOptions({
  name: 'ConnectorStepper',
});

const props = defineProps<{
  isEdit?: boolean;
  initialData?: Connector | null;
}>();

const loading = defineModel<boolean>('loading', { default: false });
const isOpen = defineModel<boolean>('isOpen', { required: true });
const emit = defineEmits<{
  (e: 'save', payload: { type: string; data: Connector }): void;
}>();

// --- STATE ---
const { t } = useI18n();
const { confirm } = useDialog();
const step = ref(1);
const subStep = ref(1); // Added sub-step for vertical stepper
const selectedType = ref<string>('');
const selectedProvider = ref<string>('');
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const activeForm = ref<any>(null);
const aclMode = ref<string>('public');
const connectorData = ref<Connector>(new Connector()); // Active connector being configured

// Smart Metadata Extraction
const smartExtractionEnabled = ref(false);
const showAdvancedSettings = ref(false);

const settingsMap = ref<Record<string, string>>({});

// ACL Modes
const aclModes = computed(() => [
  {
    id: 'public',
    name: t('aclPublic'),
    description: t('aclPublicDesc'),
    icon: 'public',
    color: 'positive',
  },
  {
    id: 'restricted',
    name: t('aclRestricted'),
    description: t('aclRestrictedDesc'),
    icon: 'lock',
    color: 'warning',
  },
]);

// AI Providers (Centralized logic)
const { embeddingProviderOptions: aiProviders } = useAiProviders(settingsMap);

// Forms mapping
const forms: Record<string, Component> = {
  sql: SqlForm,
  local_folder: FolderForm,
  local_file: ConnectorFileForm,
};

// --- COMPUTED ---
const isNextDisabled = computed(() => {
  if (step.value === 1) return !selectedType.value;
  if (step.value === 2) return false; // Handled by form.submit()
  if (step.value === 3) return !selectedProvider.value; // Enforce provider selection
  // Step 4 (Schedule) - always valid (defaults to manual)
  if (step.value === 5) {
    return (
      aclMode.value === 'restricted' &&
      (!connectorData.value.configuration.connector_acl ||
        connectorData.value.configuration.connector_acl.length === 0)
    );
  }
  return false;
});

const currentForm = computed<Component | undefined>(() => {
  return forms[selectedType.value];
});

// --- WATCHERS ---
// Initialize connector data when moving to Step 2 (Configuration)
watch([step, selectedType], () => {
  if (step.value === 2) {
    const backendType = selectedType.value as ConnectorType;

    // Only reset if type changed or purely new
    if (connectorData.value.connector_type !== backendType && !props.isEdit) {
      connectorData.value = new Connector({ connector_type: backendType });
    }
  }
});

// Sync AI Provider when moving to next steps or when selected
watch(selectedProvider, (val) => {
  if (!connectorData.value.configuration) connectorData.value.configuration = {};
  connectorData.value.configuration.ai_provider = val;
});

// Watch for dialog close to reset state
watch(
  isOpen,
  (val) => {
    if (val) {
      // Check settings every time dialog opens to ensure enabled/disabled states are fresh
      void loadSettings();
      if (props.isEdit && props.initialData) {
        initializeEditMode();
      } else {
        resetState();
      }
    } else {
      setTimeout(resetState, 300);
    }
  },
  { immediate: true },
);

onMounted(() => {
  // Try to load settings on mount as well, just in case
  void loadSettings();
});

// Watch for ACL mode changes
watch(aclMode, (newMode) => {
  if (!connectorData.value.configuration) {
    connectorData.value.configuration = {};
  }
  if (!connectorData.value.configuration.connector_acl) {
    connectorData.value.configuration.connector_acl = [];
  }

  const currentTags = connectorData.value.configuration.connector_acl;

  if (newMode === 'public') {
    if (!currentTags.includes('public')) {
      currentTags.push('public');
    }
  } else if (newMode === 'restricted') {
    const pubIndex = currentTags.indexOf('public');
    if (pubIndex !== -1) {
      currentTags.splice(pubIndex, 1);
    }
  }
});

// --- FUNCTIONS ---

function resetState() {
  step.value = 1;
  subStep.value = 1;
  selectedType.value = '';
  selectedProvider.value = '';
  aclMode.value = 'public';
  smartExtractionEnabled.value = false;
  connectorData.value = new Connector();
}

function initializeEditMode() {
  if (!props.initialData) return;

  // Clone data to avoid mutating prop directly
  connectorData.value = new Connector(props.initialData);
  // Deep clone config
  if (props.initialData.configuration) {
    connectorData.value.configuration = JSON.parse(JSON.stringify(props.initialData.configuration));
  }

  selectedType.value = mapBackendToUiType(connectorData.value);

  // Setup Provider
  selectedProvider.value = connectorData.value.configuration?.ai_provider || 'gemini';

  // Setup ACL
  const acl = connectorData.value.configuration?.connector_acl || [];
  if (acl.includes('public') && acl.length === 1) {
    aclMode.value = 'public';
  } else {
    aclMode.value = 'restricted';
  }

  // Smart Extraction
  smartExtractionEnabled.value =
    connectorData.value.configuration?.indexing_config?.use_smart_extraction || false;

  // Skip to step 2 directly? Or stay at 1?
  // User requested "header navigable", and presumably we start at step 1 (Type) or Step 2 (Config).
  // Use step 2 as type is fixed.
  step.value = 2;

  // Capture initial state
  initialStateJSON.value = JSON.stringify(connectorData.value);
}

const initialStateJSON = ref('');

function hasUnsavedChanges(): boolean {
  // If not edit mode and step > 1, assume likely changes if user entered data
  // But strict comparison is better.
  // For create mode, we can stick to step > 1 check OR compare with empty default.
  // Let's rely on JSON comparison even for create if we captured "empty" state.
  // Although simplify: Edit mode -> compare JSON. Create mode -> step > 1.
  if (props.isEdit) {
    return JSON.stringify(connectorData.value) !== initialStateJSON.value;
  }
  return step.value > 1;
}

function mapBackendToUiType(connector: Connector): string {
  if (connector.connector_type === ConnectorType.LOCAL_FOLDER) return 'local_folder';
  if (connector.connector_type === ConnectorType.LOCAL_FILE) return 'local_file';
  return connector.connector_type;
}

function handleClose() {
  // Check for unsaved changes
  if (hasUnsavedChanges()) {
    confirm({
      title: t('unsavedChanges'),
      message: t('unsavedChangesMessage'),
      confirmLabel: t('discard'),
      confirmColor: 'negative',
      cancelLabel: t('keepEditing'),
      onConfirm: () => {
        // Clean up uploaded file if exists
        void cleanupTempFile();
        isOpen.value = false;
      },
      onCancel: () => {}, // Explicit empty handler to fix type error if confirm requires it
    });
    return;
  }

  // No changes or safe to close
  isOpen.value = false;
}

async function cleanupTempFile() {
  try {
    const path = connectorData.value.configuration?.path;
    if (path && path.startsWith('temp_uploads')) {
      await connectorService.deleteTempFile(path);
    }
  } catch (error) {
    // Silent fail - file might already be deleted or not exist
    console.warn('Failed to cleanup temp file:', error);
  }
}

function handleBack() {
  // If we are on the configuration step (2), check if the form handles back
  if (step.value === 2 && activeForm.value && typeof activeForm.value.back === 'function') {
    const handled = activeForm.value.back();
    if (handled) return;
  }

  // Handle sub-step back navigation for Step 3
  if (step.value === 3 && subStep.value === 2) {
    subStep.value = 1;
    return;
  }

  if (step.value > 1) step.value--;
}

async function handleNext() {
  if (step.value === 2) {
    // Validate configuration form at Step 2
    if (activeForm.value) {
      // Check if submit method exists
      const form = activeForm.value;
      if (typeof form.submit === 'function') {
        const success = await form.submit();
        if (!success) return;
      }
    }
  }

  // Handle sub-step navigation for Step 3
  if (step.value === 3) {
    if (subStep.value === 1) {
      subStep.value = 2;
      return;
    }
    // If subStep is 2, proceed to next main step
  }

  step.value++;
}

function createValue(val: string, done: (item: string, mode: 'add' | 'toggle') => void) {
  if (val.length > 0) {
    done(val, 'add');
  }
}

async function handleSave() {
  // Ensure we submit the currently active form if we are on step 2
  // This is critical for edits where the user clicks "Save" directly from the config step
  if (step.value === 2 && activeForm.value) {
    if (typeof activeForm.value.submit === 'function') {
      const success = await activeForm.value.submit();
      if (!success) return;
    }
  }

  // Ensure provider
  if (!connectorData.value.configuration) connectorData.value.configuration = {};
  connectorData.value.configuration.ai_provider = selectedProvider.value;

  // Ensure ACL
  if (aclMode.value === 'public') {
    connectorData.value.configuration.connector_acl = ['public'];
  }
  // If restricted, values are already in connectorData.configuration.connector_acl via v-model

  // Smart Metadata Extraction Config
  connectorData.value.configuration.indexing_config = {
    use_smart_extraction: smartExtractionEnabled.value,
  };

  // Ensure Schedule
  if (connectorData.value.schedule_cron) {
    connectorData.value.schedule_type = ScheduleType.CRON;
  } else {
    connectorData.value.schedule_type = ScheduleType.MANUAL;
  }

  // Map UI types to backend enums
  const typeMap: Record<string, ConnectorType> = {
    folder: ConnectorType.LOCAL_FOLDER,
    file: ConnectorType.LOCAL_FILE,
  };
  connectorData.value.connector_type =
    typeMap[selectedType.value] || (selectedType.value as ConnectorType);

  emit('save', { type: selectedType.value, data: connectorData.value });
}

async function loadSettings() {
  try {
    const allSettings = await settingsService.getAll();
    allSettings.forEach((s) => {
      settingsMap.value[s.key] = s.value;
    });
  } catch (e) {
    console.error('Failed to load settings for providers check', e);
  }
}

function handleAdvancedSettingsUpdate(payload: { chunkSize: number; chunkOverlap: number }) {
  if (!connectorData.value.configuration) {
    connectorData.value.configuration = {};
  }
  connectorData.value.configuration.chunk_size = payload.chunkSize;
  connectorData.value.configuration.chunk_overlap = payload.chunkOverlap;
}
</script>

<style scoped>
/* Quasar Overrides */
:deep(.q-stepper__step-inner) {
  padding-bottom: 0 !important;
}

.bg-dark-page {
  background-color: #121212;
}

.max-width-container {
  max-width: 1200px;
  margin: 0 auto;
}

.border-bottom {
  border-bottom: 1px solid var(--q-third);
}

.border-top {
  border-top: 1px solid var(--q-third);
}

.selection-card {
  background: var(--q-secondary);
  border: 1px solid var(--q-third);
  transition: all 0.3s ease;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.selection-card:hover {
  border-color: var(--q-accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.selection-card.disabled:not(.selected) {
  opacity: 0.5;
  filter: grayscale(100%);
  cursor: not-allowed !important;
  transform: none !important;
  box-shadow: none !important;
  border-color: var(--q-third) !important;
}
.selection-card.selected {
  border-color: var(--q-accent);
  background: #252525;
  box-shadow: 0 0 0 2px var(--q-accent);
}

.selected-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}

/* Hide scrollbar for Chrome, Safari and Opera */
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbar for IE, Edge and Firefox */
.hide-scrollbar {
  -ms-overflow-style: none; /* IE and Edge */
  scrollbar-width: none; /* Firefox */
}
</style>
