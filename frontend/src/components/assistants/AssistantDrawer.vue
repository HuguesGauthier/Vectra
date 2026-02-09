<template>
  <q-dialog v-model="isOpen" maximized position="right">
    <q-card class="column bg-primary" style="width: 50vw">
      <!-- Header -->
      <div class="q-pa-md bg-primary border-bottom row items-center justify-between">
        <div class="text-h6">{{ isEdit ? formData.name : t('newAssistant') }}</div>
        <q-btn flat round dense icon="close" @click="handleClose" />
      </div>

      <!-- Tabs Navigation -->
      <div class="q-px-md q-pt-md bg-primary">
        <q-tabs
          v-model="activeTab"
          dense
          align="justify"
          class="modern-tabs"
          active-color="white"
          indicator-color="transparent"
          no-caps
          outside-arrows
          mobile-arrows
        >
          <q-tab name="general" icon="badge" :label="$t('stepGeneral')" />
          <q-tab name="knowledge" icon="hub" :label="$t('stepKnowledge')" />
          <q-tab name="personality" icon="face" :label="$t('stepPersonality')" />
          <q-tab name="intelligence" icon="psychology" :label="$t('stepIntelligence')" />
          <q-tab name="retrieval" icon="manage_search" :label="$t('retrievalStrategy')" />
          <q-tab name="performance" icon="speed" :label="$t('wizard.stepPerformanceTitle')" />
        </q-tabs>
      </div>

      <!-- Tab Panels -->
      <q-form ref="formRef" @submit="onSubmit" class="col column">
        <q-tab-panels v-model="activeTab" animated class="col scroll bg-primary">
          <!-- Tab 1: General Information -->
          <q-tab-panel name="general" class="q-pa-none">
            <q-splitter
              v-model="splitterModel"
              style="height: 100%"
              disable
              separator-style="background-color: var(--q-third)"
            >
              <template v-slot:before>
                <q-tabs
                  v-model="generalTab"
                  vertical
                  class="q-pa-sm"
                  active-color="accent"
                  indicator-color="transparent"
                  no-caps
                >
                  <q-tab name="info" icon="info" :label="$t('stepGeneral')" />
                  <q-tab name="appearance" icon="palette" :label="$t('appearance')" />
                  <q-tab name="security" icon="security" :label="$t('security')" />
                </q-tabs>
              </template>

              <template v-slot:after>
                <q-tab-panels
                  v-model="generalTab"
                  animated
                  vertical
                  transition-prev="jump-up"
                  transition-next="jump-up"
                  class="bg-primary full-height"
                >
                  <q-tab-panel name="info" class="q-pa-none">
                    <div class="q-pa-md">
                      <AssistantGeneralStep v-model="formData" hide-title />
                    </div>
                  </q-tab-panel>

                  <q-tab-panel name="appearance" class="q-pa-none">
                    <div class="q-pa-md">
                      <AssistantAppearance
                        :name="formData.name || ''"
                        :bg-color="formData.avatar_bg_color || ''"
                        :text-color="formData.avatar_text_color || ''"
                        :assistant-id="formData.id"
                        :avatar-image="formData.avatar_image"
                        :avatar-position-y="formData.avatar_vertical_position"
                        @update:bg-color="(val: string) => (formData.avatar_bg_color = val)"
                        @update:text-color="(val: string) => (formData.avatar_text_color = val)"
                        @update:avatar-position-y="
                          (val: number) => (formData.avatar_vertical_position = val)
                        "
                        @avatar-updated="
                          (val: string | null) => (formData.avatar_image = val || '')
                        "
                        @file-selected="handleAvatarFile"
                      />
                    </div>
                  </q-tab-panel>

                  <q-tab-panel name="security" class="q-pa-none">
                    <div class="q-pa-md">
                      <AssistantSecurityStep v-model="formData" />
                    </div>
                  </q-tab-panel>
                </q-tab-panels>
              </template>
            </q-splitter>
          </q-tab-panel>

          <!-- Tab 2: Knowledge Base -->
          <q-tab-panel name="knowledge">
            <AssistantKnowledgeStep
              v-model="formData"
              :connectors="availableConnectors"
              :available-tags="availableTags"
              :loading-connectors="loadingConnectors"
              hide-title
              full-width
            />
          </q-tab-panel>

          <!-- Tab 3: Personality -->
          <q-tab-panel name="personality">
            <AssistantPersonalityStep v-model="formData" :hide-title="true" />
          </q-tab-panel>

          <!-- Tab 4: Intelligence -->
          <q-tab-panel name="intelligence">
            <AssistantIntelligenceStep v-model="formData" :hide-title="true" />
          </q-tab-panel>

          <!-- Tab 5: Retrieval Strategy -->
          <q-tab-panel name="retrieval">
            <AssistantRetrievalStep v-model="formData" :hide-title="true" />
          </q-tab-panel>

          <!-- Tab 6: Performance -->
          <q-tab-panel name="performance">
            <AssistantPerformanceStep v-model="formData" :hide-title="true" />
          </q-tab-panel>
        </q-tab-panels>
      </q-form>

      <!-- Footer Actions -->
      <div class="q-pa-md border-top row justify-end bg-primary">
        <div class="q-gutter-sm">
          <q-btn
            :label="t('cancel')"
            @click="handleClose"
            style="background-color: var(--q-accent)"
            unelevated
            color="accent"
          />
          <q-btn
            unelevated
            :label="t('saveAssistant')"
            color="accent"
            @click="submitForm"
            :loading="loading"
          />
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue';

import { useI18n } from 'vue-i18n';
import type { Assistant } from 'src/services/assistantService';
import { useDialog } from 'src/composables/useDialog';
import { useAssistantForm } from 'src/composables/useAssistantForm';
import AssistantIntelligenceStep from './steps/AssistantIntelligenceStep.vue';
import AssistantRetrievalStep from './steps/AssistantRetrievalStep.vue';
import AssistantAppearance from './AssistantAppearance.vue';
import AssistantGeneralStep from './steps/AssistantGeneralStep.vue';
import AssistantKnowledgeStep from './steps/AssistantKnowledgeStep.vue';
import AssistantPersonalityStep from './steps/AssistantPersonalityStep.vue';
import AssistantSecurityStep from './steps/AssistantSecurityStep.vue'; // Security Step Component

import AssistantPerformanceStep from './steps/AssistantPerformanceStep.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'AssistantDrawer',
});

const props = defineProps<{
  modelValue: boolean;
  assistantToEdit?: Assistant | null;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'save', assistant: Partial<Assistant>): void;
}>();

// --- STATE ---
const { t } = useI18n();
const { confirm } = useDialog();

const formRef = ref();
const activeTab = ref('general');
const splitterModel = ref(20);
const generalTab = ref('info');

// Use Composable
const {
  formData,
  loadConnectors,
  loadingConnectors,
  connectors: availableConnectors, // Alias to match template
  availableTags,
  setFormData,
  defaultData,
} = useAssistantForm();

const loading = ref(false); // Local loading state for save operation

// Set default instruction using i18n after setup
const initialDataStr = ref('');

// --- COMPUTED ---
const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => {
    if (!val) handleClose();
    else emit('update:modelValue', val);
  },
});

const isEdit = computed(() => !!props.assistantToEdit);

// --- WATCHERS ---
watch(
  () => props.assistantToEdit,
  (newVal) => {
    if (newVal) {
      setFormData(newVal);
      // Ensure specific sorting/structure unique to drawer if needed
      if (newVal.linked_connectors) {
        formData.value.linked_connector_ids = newVal.linked_connectors.map((c) => c.id).sort();
      }
    } else {
      setFormData(defaultData);
      // Ensure config object exists
      if (!formData.value.configuration) {
        formData.value.configuration = { temperature: 0.1, tags: [] };
      }
    }
    initialDataStr.value = JSON.stringify(formData.value);
  },
  { immediate: true },
);

// Auto-sync happens in composable now

watch(
  () => t('defaultSystemInstructions'),
  (newVal) => {
    if (!formData.value.instructions && !isEdit.value) {
      formData.value.instructions = newVal;
    }
  },
  { immediate: true },
);

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      try {
        await loadConnectors(); // Refresh connectors when drawer opens

        if (props.assistantToEdit) {
          // Refreshed logic inside assistantToEdit watcher already handles data set
          // Force re-set to be safe if prop didn't change but drawer reopened
          setFormData(props.assistantToEdit);
          if (props.assistantToEdit.linked_connectors) {
            formData.value.linked_connector_ids = props.assistantToEdit.linked_connectors
              .map((c) => c.id)
              .sort();
          }
        } else {
          // Reset to default
          setFormData(defaultData);
          if (!formData.value.configuration) {
            formData.value.configuration = { temperature: 0.1, tags: [] };
          }
        }

        await nextTick();
        initialDataStr.value = JSON.stringify(formData.value);
        formRef.value?.resetValidation();
      } finally {
        // empty
      }
    }
  },
);

onMounted(() => {
  // void loadConnectors();
});

// --- FUNCTIONS ---
function handleClose() {
  const currentDataStr = JSON.stringify(formData.value);
  if (currentDataStr !== initialDataStr.value) {
    confirm({
      title: t('unsavedChanges'),
      message: t('unsavedChangesMessage'),
      confirmLabel: t('discard'),
      confirmColor: 'negative',
      cancelLabel: t('keepEditing'),
      onConfirm: () => {
        emit('update:modelValue', false);
      },
    });
  } else {
    emit('update:modelValue', false);
  }
}

function submitForm() {
  // Validate form locally
  formRef.value.submit();
}

function onSubmit() {
  loading.value = true;
  try {
    emit('save', { ...formData.value });
  } finally {
    loading.value = false;
  }
}

function handleAvatarFile(file: File | null) {
  formData.value.avatar_image = file ? URL.createObjectURL(file) : '';
}
</script>

<style scoped>
.border-top {
  border-top: 1px solid var(--q-sixth);
}
.border-bottom {
  border-bottom: 1px solid var(--q-sixth);
}
.ring-2 {
  border: 2px solid var(--q-secondary);
  transform: scale(1.1);
}

/* Ensure textarea fills height in the dialog */
:deep(.full-height-textarea .q-field__control),
:deep(.full-height-textarea .q-field__native) {
  height: 100%;
}
.q-btn {
  border-radius: 8px !important;
}

.connector-card {
  transition: all 0.2s ease;
  cursor: pointer;
  background-color: rgba(255, 255, 255, 0.05);
}

.connector-card:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.connector-selected {
  border-color: var(--q-accent) !important;
  background-color: rgba(var(--q-accent-rgb), 0.1);
}

/* Modern Tabs Styling */
.modern-tabs {
  background: transparent;
}

:deep(.modern-tabs .q-tab) {
  border-radius: 8px;
  margin-right: 8px;
  min-height: 36px;
  padding: 0 16px;
  transition: all 0.3s ease;
  opacity: 0.7;
  border: 1px solid transparent;
  color: var(--q-text-sub);
}

:deep(.modern-tabs .q-tab:hover) {
  opacity: 1;
  background: rgba(255, 255, 255, 0.05);
  color: var(--q-text-main);
}

:deep(.modern-tabs .q-tab--active) {
  opacity: 1;
  background: var(--q-accent);
  color: white !important;
  border-color: var(--q-accent);
  box-shadow: 0 4px 12px rgba(var(--q-accent-rgb), 0.3);
}

/* Hide the default ripple for a cleaner feel if desired, or keep it */
:deep(.modern-tabs .q-focus-helper) {
  display: none;
}
</style>
