<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card class="bg-primary column full-height" style="min-width: 65vw">
      <!-- Header -->
      <div class="q-pa-md bg-primary row items-center justify-between">
        <div class="text-h6 text-weight-bold">
          {{ $t('createNewAssistant') }}
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
        >
          <q-step :name="1" :title="$t('stepGeneral')" icon="smart_toy" :done="step > 1" />
          <q-step :name="2" :title="$t('stepKnowledge')" icon="hub" :done="step > 2" />
          <q-step :name="3" :title="$t('stepPersonality')" icon="face" :done="step > 3" />
          <q-step :name="4" :title="$t('stepIntelligence')" icon="psychology" :done="step > 4" />
          <q-step
            :name="5"
            :title="$t('retrievalStrategy')"
            icon="manage_search"
            :done="step > 5"
          />

          <!-- Step 6 (Performance) -->
          <q-step
            :name="6"
            :title="$t('wizard.stepPerformanceTitle')"
            icon="speed"
            :done="step > 6"
          />
        </q-stepper>
      </div>

      <!-- Content Area -->
      <div class="col scroll q-pa-lg relative-position bg-primary">
        <q-form ref="formRef" class="full-height">
          <!-- Step 1: General Information -->
          <div v-if="step === 1">
            <q-stepper
              v-model="innerStep"
              vertical
              color="accent"
              active-color="accent"
              done-color="positive"
              animated
              flat
              class="bg-transparent"
            >
              <q-step :name="1" :title="$t('stepGeneral')" icon="badge" :done="innerStep > 1">
                <AssistantGeneralStep v-model="assistantData" />
              </q-step>

              <q-step :name="2" :title="$t('appearance')" icon="palette" :done="innerStep > 2">
                <div class="row justify-center">
                  <div class="col-12 col-md-8">
                    <AssistantAppearance
                      :name="assistantData.name || ''"
                      :bg-color="assistantData.avatar_bg_color || ''"
                      :text-color="assistantData.avatar_text_color || ''"
                      :assistant-id="assistantData.id"
                      :avatar-image="assistantData.avatar_image"
                      :avatar-position-y="assistantData.avatar_vertical_position"
                      @update:bg-color="(val: string) => (assistantData.avatar_bg_color = val)"
                      @update:text-color="(val: string) => (assistantData.avatar_text_color = val)"
                      @update:avatar-position-y="
                        (val: number) => (assistantData.avatar_vertical_position = val)
                      "
                      @avatar-updated="
                        (val: string | null) => (assistantData.avatar_image = val || '')
                      "
                      @file-selected="(file: File | null) => (avatarFile = file)"
                    />
                  </div>
                </div>
              </q-step>

              <q-step :name="3" :title="$t('security')" icon="security" :done="innerStep > 3">
                <div class="row justify-center">
                  <div class="col-12 col-md-8">
                    <AssistantSecurityStep v-model="assistantData" />
                  </div>
                </div>
              </q-step>
            </q-stepper>
          </div>

          <!-- Step 4: Intelligence -->
          <div v-if="step === 4" class="row justify-center">
            <AssistantIntelligenceStep v-model="assistantData" />
          </div>

          <!-- Step 6: Performance -->
          <div v-if="step === 6" class="row justify-center full-width">
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

          <!-- Step 5: Retrieval Strategy -->
          <div v-if="step === 5">
            <q-stepper
              v-model="innerStep"
              vertical
              color="accent"
              active-color="accent"
              done-color="positive"
              animated
              flat
              class="bg-transparent"
            >
              <q-step
                :name="1"
                :title="$t('retrievalVolumeAndRelevance')"
                icon="manage_search"
                :done="innerStep > 1"
              >
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <RetrievalParams v-model="assistantData" hide-title section="basic" />
                  </div>
                </div>
              </q-step>

              <q-step :name="2" :title="$t('precisionBoost')" icon="bolt" :done="innerStep > 2">
                <div class="row justify-center">
                  <div class="col-12 col-md-10">
                    <RetrievalParams v-model="assistantData" hide-title section="rerank" />
                  </div>
                </div>
              </q-step>
            </q-stepper>
          </div>

          <!-- Step 3: Personality/Instructions -->
          <div v-if="step === 3" class="row justify-center">
            <AssistantPersonalityStep v-model="assistantData" />
          </div>

          <!-- Step 2: Knowledge Base -->
          <div v-if="step === 2" class="row justify-center">
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
        </q-form>
      </div>

      <!-- Footer Actions -->
      <div class="q-pa-md bg-primary border-top row justify-between items-center">
        <q-btn
          v-if="step > 1 || (step === 1 && innerStep > 1)"
          flat
          color="grey-5"
          :label="$t('back')"
          icon="arrow_back"
          @click="handleBack"
        />
        <div v-else></div>

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
            !assistantData.linked_connector_ids || assistantData.linked_connector_ids.length === 0
          "
          @click="handleSave"
        />
      </div>

      <!-- New Component Usage -->
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
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
  name: 'AddAssistantStepper',
});

defineProps<{
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
const innerStep = ref(1);
const formRef = ref();
const avatarFile = ref<File | null>(null);

// Use Composable
const {
  formData: assistantData, // Alias to keep template working with minimal changes
  loadConnectors,
  loadingConnectors,
  connectors,
  availableTags,
  resetForm,
} = useAssistantForm();

const showKnowledgeError = ref(false);

watch(
  () => assistantData.value.linked_connector_ids,
  (newVal) => {
    if (newVal && newVal.length > 0) {
      showKnowledgeError.value = false;
    }
  },
);

// AI Models - map from centralized chat providers

// --- WATCHERS ---
watch(isOpen, async (val) => {
  if (val) {
    resetState();
    // Load default instructions
    if (!assistantData.value.instructions) {
      assistantData.value.instructions = t('defaultSystemInstructions');
    }
    await loadConnectors();
  }
});

// --- FUNCTIONS ---

function resetState() {
  step.value = 1;
  innerStep.value = 1;
  resetForm();
}

function handleClose() {
  if (step.value > 1 || assistantData.value.name) {
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
  if (step.value === 1 || step.value === 5) {
    if (innerStep.value > 1) {
      innerStep.value--;
      return;
    }
  }
  if (step.value > 1) {
    step.value--;
    // Reset innerStep to max if previous step has sub-steps, or 1
    if (step.value === 1) {
      innerStep.value = 3;
    } else {
      innerStep.value = 1;
    }
  }
}

async function handleNext() {
  const valid = await formRef.value?.validate();
  if (valid) {
    if (step.value === 1) {
      if (innerStep.value < 3) {
        innerStep.value++;
        return;
      }
    }

    if (step.value === 5) {
      if (innerStep.value < 2) {
        innerStep.value++;
        return;
      }
    }

    // Validate Step 2: Knowledge Base
    if (step.value === 2) {
      if (
        !assistantData.value.linked_connector_ids ||
        assistantData.value.linked_connector_ids.length === 0
      ) {
        showKnowledgeError.value = true;
        // useNotification().notifyError(t('validate.atLeastOneSource'));
        return;
      }
    }

    step.value++;
    innerStep.value = 1; // Reset inner step when moving to a new main step
  }
}

function handleSave() {
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

.border-accent {
  border-color: var(--q-accent) !important;
  border-width: 2px;
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
  transform: translateY(-4px);
  border-color: var(--q-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
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

/* Ensure textarea fills height in the dialog */
:deep(.full-height-textarea .q-field__control),
:deep(.full-height-textarea .q-field__native) {
  height: 100%;
  min-height: 300px;
}

:deep(.q-stepper__step-inner) {
  padding: 0;
}
</style>
