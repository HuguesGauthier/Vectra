<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card class="column bg-primary" style="width: 1200px; max-width: 95vw; height: 90vh;">
      <!-- Header -->
      <div class="q-pa-md bg-primary border-bottom row items-center justify-between">
        <div class="text-h6 text-weight-bold">
          {{ isEdit ? $t('editAssistant') : $t('createNewAssistant') }}
        </div>
        <q-btn flat round dense icon="close" @click="handleClose" />
      </div>

      <!-- Stepper Header -->
      <div class="bg-primary border-bottom">
        <q-stepper
          v-model="step"
          ref="stepper"
          color="accent"
          alternative-labels
          active-color="accent"
          done-color="positive"
          animated
          flat
          class="bg-transparent"
          :header-nav="isEdit"
        >
          <q-step
            :name="1"
            :title="$t('stepGeneral')"
            icon="smart_toy"
            :done="step > 1"
            :error="isEdit && stepErrors.has(1)"
          />
          <q-step
            :name="2"
            :title="$t('stepKnowledge')"
            icon="hub"
            :done="step > 2"
            :error="isEdit && stepErrors.has(2)"
          />
          <q-step
            :name="3"
            :title="$t('stepPersonality')"
            icon="face"
            :done="step > 3"
            :error="isEdit && stepErrors.has(3)"
          />
          <q-step
            :name="4"
            :title="$t('stepIntelligence')"
            icon="psychology"
            :done="step > 4"
            :error="isEdit && stepErrors.has(4)"
          />
          <q-step
            :name="5"
            :title="$t('retrievalStrategy')"
            icon="manage_search"
            :done="step > 5"
            :error="isEdit && stepErrors.has(5)"
          />
          <q-step
            :name="6"
            :title="$t('wizard.stepPerformanceTitle')"
            icon="speed"
            :done="step > 6"
            :error="isEdit && stepErrors.has(6)"
          />
        </q-stepper>
      </div>

      <!-- Content Area -->
      <div class="col scroll q-pa-lg relative-position bg-primary">
        <q-form ref="formRef" class="full-height" @submit.prevent>
          <!-- Step 1: General Information -->
          <div v-show="step === 1">
            <q-tabs
              v-model="innerStep"
              dense
              align="justify"
              class="q-mb-md"
              active-color="accent"
              indicator-color="accent"
              narrow-indicator
            >
              <q-tab :name="1" :label="$t('stepGeneral')" icon="badge" />
              <q-tab :name="2" :label="$t('appearance')" icon="palette" />
              <q-tab :name="3" :label="$t('security')" icon="security" />
            </q-tabs>

            <q-tab-panels v-model="innerStep" animated class="bg-transparent">
              <q-tab-panel :name="1" class="q-pa-none">
                <AssistantGeneralStep v-model="assistantData" />
              </q-tab-panel>

              <q-tab-panel :name="2" class="q-pa-none">
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <AssistantAppearance
                      :name="assistantData.name || ''"
                      :bg-color="assistantData.avatar_bg_color || ''"
                      :text-color="assistantData.avatar_text_color || ''"
                      :assistant-id="assistantData.id"
                      :avatar-image="assistantData.avatar_image"
                      :avatar-position-y="assistantData.avatar_vertical_position"
                      @update:bg-color="(val) => (assistantData.avatar_bg_color = val)"
                      @update:text-color="(val) => (assistantData.avatar_text_color = val)"
                      @update:avatar-position-y="
                        (val) => (assistantData.avatar_vertical_position = val)
                      "
                      @avatar-updated="(val) => (assistantData.avatar_image = val || '')"
                      @file-selected="(file) => (avatarFile = file)"
                    />
                  </div>
                </div>
              </q-tab-panel>

              <q-tab-panel :name="3" class="q-pa-none">
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <AssistantSecurityStep v-model="assistantData" />
                  </div>
                </div>
              </q-tab-panel>
            </q-tab-panels>
          </div>

          <!-- Step 2: Knowledge Base -->
          <div v-show="step === 2" class="row justify-center">
            <div class="col-12">
              <AssistantKnowledgeStep
                v-model="assistantData"
                :connectors="connectors"
                :available-tags="availableTags"
                :loading-connectors="loadingConnectors"
                :error="showKnowledgeError"
                :error-message="$t('validate.atLeastOneSource')"
              />
            </div>
          </div>

          <!-- Step 3: Personality/Instructions -->
          <div v-show="step === 3" class="row justify-center">
            <AssistantPersonalityStep v-model="assistantData" />
          </div>

          <!-- Step 4: Intelligence -->
          <div v-show="step === 4" class="row justify-center">
            <AssistantIntelligenceStep v-model="assistantData" />
          </div>

          <!-- Step 5: Retrieval Strategy -->
          <div v-show="step === 5">
            <q-tabs
              v-model="retrievalStep"
              dense
              align="justify"
              class="q-mb-md"
              active-color="accent"
              indicator-color="accent"
              narrow-indicator
            >
              <q-tab :name="1" :label="$t('retrievalVolumeAndRelevance')" icon="manage_search" />
              <q-tab :name="2" :label="$t('precisionBoost')" icon="bolt" />
            </q-tabs>

            <q-tab-panels v-model="retrievalStep" animated class="bg-transparent">
              <q-tab-panel :name="1" class="q-pa-none">
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <RetrievalParams v-model="assistantData" hide-title section="basic" />
                  </div>
                </div>
              </q-tab-panel>

              <q-tab-panel :name="2" class="q-pa-none">
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <RetrievalParams v-model="assistantData" hide-title section="rerank" />
                  </div>
                </div>
              </q-tab-panel>
            </q-tab-panels>
          </div>

          <!-- Step 6: Performance -->
          <div v-show="step === 6" class="row justify-center full-width">
            <div class="col-12">
              <div class="text-subtitle1 q-mb-xl text-center">
                {{ $t('wizard.stepPerformanceCaption') }}
              </div>

              <div class="row justify-center">
                <div class="col-10">
                  <AssistantPerformanceStep v-model="assistantData" hide-title />
                </div>
              </div>
            </div>
          </div>
        </q-form>
      </div>

      <!-- Footer Actions -->
      <div class="q-pa-md bg-primary border-top row justify-between items-center">
        <!-- Left Side: Back Button (Only in Create Mode or if not first step?) -->
        <div>
          <q-btn
            v-if="!isEdit && step > 1"
            flat
            color="grey-5"
            :label="$t('back')"
            icon="arrow_back"
            @click="handleBack"
          />
        </div>

        <!-- Right Side: Navigation & Save -->
        <div class="row q-gutter-sm">
          <!-- Create Mode Navigation -->
          <template v-if="!isEdit">
            <q-btn
              v-if="step < 6"
              color="accent"
              :label="$t('next')"
              icon-right="arrow_forward"
              @click="handleNext"
            />
            <q-btn
              v-else
              color="positive"
              :label="$t('createAssistant')"
              icon="check"
              :loading="loading"
              :disable="
                !assistantData.linked_connector_ids ||
                assistantData.linked_connector_ids.length === 0
              "
              @click="handleSave"
            />
          </template>

          <!-- Edit Mode Actions -->
          <template v-else>
            <q-btn
              :label="$t('cancel')"
              flat
              color="grey-5"
              @click="handleClose"
            />
            <q-btn
              color="accent"
              :label="$t('save')"
              :loading="loading"
              @click="handleSave"
            />
          </template>
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import type { Assistant } from 'src/services/assistantService';
import { useDialog } from 'src/composables/useDialog';
import { useAssistantForm } from 'src/composables/useAssistantForm';
import AssistantPerformanceStep from './steps/AssistantPerformanceStep.vue';
import AssistantGeneralStep from './steps/AssistantGeneralStep.vue';
import AssistantKnowledgeStep from './steps/AssistantKnowledgeStep.vue';
import AssistantPersonalityStep from './steps/AssistantPersonalityStep.vue';
import AssistantIntelligenceStep from './steps/AssistantIntelligenceStep.vue';
import RetrievalParams from './RetrievalParams.vue';
import AssistantAppearance from './AssistantAppearance.vue';
import AssistantSecurityStep from './steps/AssistantSecurityStep.vue';

defineOptions({
  name: 'AssistantStepper',
});

const props = defineProps<{
  assistantToEdit?: Assistant | null;
  loading?: boolean;
}>();

const isOpen = defineModel<boolean>('isOpen', { required: true });

const emit = defineEmits<{
  (e: 'save', data: Partial<Assistant>, file?: File | null): void;
}>();

// --- STATE ---
const { t } = useI18n();
const { confirm } = useDialog();

const step = ref(1);
const innerStep = ref(1); // Tabs for General Step in Create Config
const retrievalStep = ref(1); // Tabs for Retrieval Step
const formRef = ref();
const avatarFile = ref<File | null>(null);
const stepErrors = ref(new Set<number>()); // Track invalid steps in Edit mode

// Use Composable
const {
  formData: assistantData,
  loadConnectors,
  loadingConnectors,
  connectors,
  availableTags,
  resetForm,
  setFormData,
} = useAssistantForm();

const showKnowledgeError = ref(false);

const isEdit = computed(() => !!props.assistantToEdit);

// --- WATCHERS ---

watch(
  () => assistantData.value.linked_connector_ids,
  (newVal) => {
    if (newVal && newVal.length > 0) {
      showKnowledgeError.value = false;
    }
  },
);

watch(isOpen, async (val) => {
  if (val) {
    if (props.assistantToEdit) {
      // Edit Mode
      setFormData(props.assistantToEdit);
      if (props.assistantToEdit.linked_connectors) {
        assistantData.value.linked_connector_ids = props.assistantToEdit.linked_connectors
          .map((c) => c.id)
          .sort();
      }
    } else {
      // Create Mode
      resetState();
      if (!assistantData.value.instructions) {
        assistantData.value.instructions = t('defaultSystemInstructions');
      }
    }
    
    await nextTick();
    formRef.value?.resetValidation();
    await loadConnectors();
  }
});

// --- FUNCTIONS ---

function resetState() {
  step.value = 1;
  innerStep.value = 1; // 1=Info, 2=Appearance, 3=Security
  retrievalStep.value = 1;
  stepErrors.value.clear();
  resetForm();
  avatarFile.value = null;
}

function handleClose() {

  // Compare with initial state if needed for "Unsaved Changes" (Simplified here)
  
  if (isEdit.value || step.value > 1 || assistantData.value.name) {
     confirm({
      title: t('unsavedChanges'),
      message: t('unsavedChangesMessage'),
      confirmLabel: t('discard'),
      confirmColor: 'negative',
      onConfirm: () => {
        isOpen.value = false;
      },
    });
  } else {
    isOpen.value = false;
  }
}

function handleBack() {
  if (step.value > 1) {
    step.value--;
  }
}

async function handleNext() {
  const valid = await formRef.value?.validate();
  
  if (valid) {
    // Custom Validations
    if (step.value === 2) { // Knowledge
      if (
        !assistantData.value.linked_connector_ids ||
        assistantData.value.linked_connector_ids.length === 0
      ) {
        showKnowledgeError.value = true;
        return;
      }
    }

    step.value++;
  }
}

async function handleSave() {
  // Validate all before save
  const valid = await formRef.value?.validate();
  
  if (!valid) {
    // If invalid, find which step (basic heuristic or just show error)
    // In stepper content, we are rendering all steps but v-show. 
    // QForm validation will trigger on all inputs.
    return;
  }

  // Knowledge validation
  if (
    !assistantData.value.linked_connector_ids ||
    assistantData.value.linked_connector_ids.length === 0
  ) {
    showKnowledgeError.value = true;
    if (isEdit.value) step.value = 2; // Jump to knowledge step
    return;
  }

  emit('save', assistantData.value, avatarFile.value);
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid var(--q-third);
}

.border-top {
  border-top: 1px solid var(--q-third);
}

/* Ensure textarea fills height in the dialog */
:deep(.full-height-textarea .q-field__control),
:deep(.full-height-textarea .q-field__native) {
  height: 100%;
  min-height: 200px;
}

:deep(.q-stepper__step-inner) {
  padding: 0;
}
</style>
