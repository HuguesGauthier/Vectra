<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card class="bg-primary column full-height" style="min-width: 55vw">
      <!-- Header -->
      <div class="q-pa-md bg-primary border-bottom row items-center justify-between">
        <div class="text-h6 text-weight-bold">
          {{ $t('addConnector', { type: '' }).replace('  ', ' ') }}
        </div>
        <q-btn flat round dense icon="close" @click="handleClose" />
      </div>

      <!-- Stepper Header -->
      <div class="bg-primary q-px-xl q-pt-md">
        <q-stepper
          v-model="step"
          ref="stepper"
          color="accent"
          active-color="accent"
          done-color="positive"
          alternative-labels
          animated
          flat
          class="bg-transparent"
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
      <div class="col scroll q-pa-lg relative-position bg-primary hide-scrollbar">
        <!-- Step 1: Connector Type Selection -->
        <ConnectorTypeStep v-if="step === 1" v-model="selectedType" />

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
              <div class="row q-col-gutter-lg justify-center">
                <div v-for="provider in aiProviders" :key="provider.id" class="col-12 col-md-4">
                  <q-card
                    class="selection-card full-height column justify-between"
                    :class="{
                      selected: selectedProvider === provider.id,
                      disabled: provider.disabled,
                    }"
                    v-ripple="!provider.disabled"
                    @click="!provider.disabled ? (selectedProvider = provider.id) : null"
                    style="min-height: 280px"
                  >
                    <div v-if="selectedProvider === provider.id" class="selected-overlay">
                      <q-icon name="check_circle" color="accent" size="32px" />
                    </div>

                    <AppTooltip v-if="provider.disabled">
                      {{ $t('engineNotConfigured') }}
                    </AppTooltip>

                    <q-card-section class="col-grow column items-center text-center q-pt-lg">
                      <div class="q-mb-md relative-position">
                        <img :src="provider.logo" style="width: 64px; height: 64px" />
                        <q-badge
                          v-if="provider.badge"
                          floating
                          :color="provider.badgeColor"
                          rounded
                          class="q-px-sm q-py-xs shadow-2"
                          style="top: -5px; right: -15px"
                        >
                          {{ provider.badge }}
                        </q-badge>
                      </div>

                      <div class="text-h6 text-weight-bold q-mb-xs">{{ provider.name }}</div>
                      <div class="text-caption text-grey-5 q-mb-md">{{ provider.tagline }}</div>

                      <div class="text-body2 text-grey-4 full-width">
                        {{ provider.description }}
                      </div>
                    </q-card-section>

                    <div class="row justify-center q-pb-md">
                      <q-btn
                        flat
                        no-caps
                        dense
                        color="accent"
                        icon="settings"
                        :label="$t('advancedSettings')"
                        size="sm"
                        :disable="provider.disabled"
                        @click.stop="showAdvancedSettings = true"
                      >
                        <q-tooltip class="text-body2">{{ $t('advancedIndexingDesc') }}</q-tooltip>
                      </q-btn>
                    </div>
                  </q-card>
                </div>
              </div>
            </q-step>

            <!-- Sub-Step 2: Smart Extraction -->
            <q-step
              :name="2"
              :title="$t('smartExtractionTitle')"
              icon="psychology"
              :done="subStep > 2"
            >
              <SmartExtractionConfig v-model="smartExtractionEnabled" />

              <q-stepper-navigation>
                <q-btn
                  flat
                  @click="subStep = 1"
                  color="primary"
                  :label="$t('back')"
                  class="q-ml-sm"
                />
              </q-stepper-navigation>
            </q-step>
          </q-stepper>

          <AdvancedIndexingSettings
            v-model:isOpen="showAdvancedSettings"
            :chunk-size="connectorData.chunk_size"
            :chunk-overlap="connectorData.chunk_overlap"
            @update="updateChunkingConfig"
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

        <div v-if="step < 5" class="row items-center">
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
          <q-btn
            color="accent"
            :label="$t('next')"
            icon-right="arrow_forward"
            :disable="isNextDisabled"
            @click="handleNext"
          />
        </div>
        <q-btn
          v-else
          color="positive"
          :label="$t('save')"
          icon="check"
          :loading="loading"
          @click="handleSave"
        />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, type Component, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Connector } from 'src/models/Connector';
import { ConnectorType, ScheduleType } from 'src/models/enums';
import FolderForm from './forms/FolderForm.vue';
import SqlForm from './forms/SqlForm.vue';
import VannaSqlForm from './forms/VannaSqlForm.vue';
import SharePointForm from './forms/SharePointForm.vue';
import ConfluenceForm from './forms/ConfluenceForm.vue';
import ConnectorFileForm from './forms/ConnectorFileForm.vue';
import SmartExtractionConfig from './fields/SmartExtractionConfig.vue';
import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';
import { useDialog } from 'src/composables/useDialog';
import { connectorService } from 'src/services/connectorService';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import AdvancedIndexingSettings from './dialogs/AdvancedIndexingSettings.vue';
import ConnectorTypeStep from './ConnectorTypeStep.vue';
import { settingsService } from 'src/services/settingsService';
import ScheduleOptions from './ScheduleOptions.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'AddConnectorStepper',
});

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

// Advanced Indexing
const showAdvancedSettings = ref(false);

// Smart Metadata Extraction
const smartExtractionEnabled = ref(false);

const settingsMap = ref<Record<string, string>>({});

function updateChunkingConfig(payload: { chunkSize: number; chunkOverlap: number }) {
  if (!connectorData.value) return;
  connectorData.value.chunk_size = payload.chunkSize;
  connectorData.value.chunk_overlap = payload.chunkOverlap;
}

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

// AI Providers
const aiProviders = computed(() => [
  {
    id: 'local',
    name: t('localEmbeddings'),
    tagline: 'Private & Secure',
    description: settingsMap.value['local_embedding_model']
      ? `${t('modelLabel')}: ${settingsMap.value['local_embedding_model']}`
      : t('localEmbeddingsDesc'),
    logo: localLogo,
    badge: t('private'),
    badgeColor: 'grey-7',
    disabled: !settingsMap.value['local_embedding_model'],
  },
  {
    id: 'gemini',
    name: t('geminiEmbeddings'),
    tagline: 'Google DeepMind',
    description: settingsMap.value['gemini_embedding_model']
      ? `${t('modelLabel')}: ${settingsMap.value['gemini_embedding_model']}`
      : t('geminiEmbeddingsDesc'),
    logo: geminiLogo,
    badge: t('public'),
    badgeColor: 'blue-6',
    disabled: !settingsMap.value['gemini_embedding_model'],
  },
  {
    id: 'openai',
    name: t('openaiEmbeddings'),
    tagline: 'Standard Industry Model',
    description: settingsMap.value['openai_embedding_model']
      ? `${t('modelLabel')}: ${settingsMap.value['openai_embedding_model']}`
      : t('openaiEmbeddingsDesc'),
    logo: openaiLogo,
    badge: t('public'),
    badgeColor: 'green-6',
    disabled: !settingsMap.value['openai_embedding_model'],
  },
]);

// Forms mapping
const forms: Record<string, Component> = {
  sharepoint: SharePointForm,
  confluence: ConfluenceForm,
  sql: SqlForm,
  vanna_sql: VannaSqlForm,
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
// Initialize connector data when moving to Step 2 (Configuration)
watch([step, selectedType], () => {
  if (step.value === 2) {
    const backendType = selectedType.value as ConnectorType;

    if (connectorData.value.connector_type !== backendType) {
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
watch(isOpen, (val) => {
  if (val) {
    // If opening with existing data (e.g. edit mode passed externally? no, this is 'AddConnectorStepper', probably mostly new)
    // But if we wanted to support pre-filling:
    // (Schedule parsing moved to component)
    // Fetch settings to update disabled states
    void loadSettings();
  } else {
    setTimeout(resetState, 300);
  }
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
  selectedType.value = '';
  selectedProvider.value = '';
  aclMode.value = 'public';
  connectorData.value = new Connector();
}

function handleClose() {
  // Check for unsaved changes if the user has started the process (step > 1)
  if (step.value > 1) {
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

function handleSave() {
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

  // Ensure Backend Type (usually already set in Step 2 watcher)
  let backendType: ConnectorType;
  if (selectedType.value === 'folder') {
    backendType = ConnectorType.LOCAL_FOLDER;
  } else if (selectedType.value === 'file') {
    backendType = ConnectorType.LOCAL_FILE;
  } else {
    backendType = selectedType.value as ConnectorType;
  }
  connectorData.value.connector_type = backendType;

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
</script>

<style scoped>
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
