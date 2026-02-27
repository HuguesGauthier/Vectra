<template>
  <div class="row justify-center full-width">
    <div class="col-10 full-height column">
      <div v-if="!hideTitle">
        <div class="text-subtitle1 text-center q-mb-lg">
          {{ $t('systemInstructionsHint') }}
        </div>
      </div>

      <q-input
        v-model="localData.instructions"
        :label="$t('systemInstructions')"
        outlined
        bg-color="secondary"
        input-class="text-main"
        label-color="sub"
        type="textarea"
        class="col"
        rows="18"
        :rules="[(val) => !!val || $t('instructionsRequired')]"
      />

      <!-- Generation Flow -->
      <div class="row q-col-gutter-md q-mt-sm">
        <!-- Step 1: Generate -->
        <div class="col-12 col-md-6">
          <div class="flow-step-card step-generate" @click="showWizard = true" v-ripple>
            <div class="row items-center no-wrap">
              <div class="step-indicator">1</div>
              <div class="q-ml-md">
                <div class="text-subtitle2 text-weight-bold">{{ $t('generateWithWizard') }}</div>
                <div class="text-caption">
                  {{ $t('wizard.step1Caption') || 'Create a structured draft' }}
                </div>
              </div>
              <q-space />
              <q-icon name="psychology" size="24px" color="accent" />
            </div>
          </div>
        </div>

        <!-- Step 2: Optimize -->
        <div class="col-12 col-md-6">
          <div
            class="flow-step-card step-optimize"
            :class="{ disabled: !localData.instructions }"
            @click="handleOptimizeInstructions"
            v-ripple
          >
            <div class="row items-center no-wrap">
              <div class="step-indicator">2</div>
              <div class="q-ml-md">
                <div class="text-subtitle2 text-weight-bold">{{ $t('optimizeWithAi') }}</div>
                <div class="text-caption text-grey-5">Refine & Polish</div>
              </div>
              <q-space />
              <div v-if="isOptimizing">
                <q-spinner color="accent" size="24px" />
              </div>
              <q-icon v-else name="auto_awesome" size="24px" color="accent" />
            </div>
          </div>
        </div>
      </div>

      <!-- Confirmation Dialog for AI Optimization -->
      <q-dialog v-model="showConfirmOptimize" persistent>
        <q-card class="bg-primary text-grey-5 border-all" style="max-width: 400px">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6 text-accent">Optimiser avec l'IA</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>

          <q-card-section class="q-pt-md">
            {{
              $t('optimizeConfirmationMessage') ||
              "L'IA va analyser et reformuler vos instructions pour les rendre plus efficaces. Votre texte actuel sera remplacé. Souhaitez-vous continuer ?"
            }}
          </q-card-section>

          <q-card-actions align="right" class="q-pa-md">
            <q-btn flat :label="$t('cancel') || 'Annuler'" color="grey-7" v-close-popup />
            <q-btn
              unelevated
              :label="$t('confirm') || 'Optimiser'"
              color="accent"
              @click="executeOptimization"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showWizard">
        <q-card style="min-width: 1000px; max-width: 95vw" class="bg-primary text-grey-5">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ $t('assistantWizard') }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>

          <q-card-section>
            <CreateAssistantStepper @submit="handleWizardSubmit" />
          </q-card-section>
        </q-card>
      </q-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAssistantForm, type WizardData } from 'src/composables/useAssistantForm';
import CreateAssistantStepper from '../CreateAssistantStepper.vue';
import type { Assistant } from 'src/services/assistantService';

defineOptions({
  name: 'AssistantPersonalityStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

// const { t } = useI18n(); // Existing files use useI18n
const { optimizeInstructions, generatePromptFromWizard } = useAssistantForm();

const showWizard = ref(false);
const showConfirmOptimize = ref(false);
const isOptimizing = ref(false);

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

function handleOptimizeInstructions() {
  if (!localData.value.instructions) return;
  showConfirmOptimize.value = true;
}

function executeOptimization() {
  showConfirmOptimize.value = false;
  isOptimizing.value = true;

  optimizeInstructions(localData.value.instructions as string)
    .then((optimized) => {
      localData.value.instructions = optimized;
    })
    .catch(() => {
      // Error handled in composable or UI
    })
    .finally(() => {
      isOptimizing.value = false;
    });
}

function handleWizardSubmit(data: WizardData) {
  const prompt = generatePromptFromWizard(data);
  localData.value.instructions = prompt;
  showWizard.value = false;
}
</script>

<style scoped>
:deep(.full-height-textarea .q-field__control),
:deep(.full-height-textarea .q-field__native) {
  height: 100%;
}

.flow-step-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.flow-step-card:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: var(--q-accent);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(var(--q-accent-rgb), 0.2);
}

.flow-step-card.disabled {
  opacity: 0.4;
  pointer-events: none;
  filter: grayscale(1);
}

.step-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--q-accent), #6e2cf2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(var(--q-accent-rgb), 0.4);
}

.step-generate:hover {
  border-color: var(--q-accent);
}

.step-optimize:hover:not(.disabled) {
  border-color: var(--q-accent);
}

:deep(.q-field--outlined .q-field__control):before {
  border-color: rgba(255, 255, 255, 0.1) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined .q-field__control):after {
  border-color: rgba(255, 255, 255, 0.1) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined.q-field--focused .q-field__control):after {
  border-color: var(--q-accent) !important;
  border-width: 2px !important;
}
</style>
