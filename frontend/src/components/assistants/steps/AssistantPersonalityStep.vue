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

      <!-- Wizard Dialog -->
      <q-dialog v-model="showWizard">
        <q-card style="min-width: 800px" class="bg-primary text-grey-5">
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
// import { useI18n } from 'vue-i18n'; // Automatically imported in Quasar usually or via composables, but best to import if explicit. Check existing files.
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
const isOptimizing = ref(false);

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

async function handleOptimizeInstructions() {
  if (!localData.value.instructions) return;
  isOptimizing.value = true;
  try {
    const optimized = await optimizeInstructions(localData.value.instructions);
    localData.value.instructions = optimized;
  } catch {
    // Error handled in composable
  } finally {
    isOptimizing.value = false;
  }
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
  border: 1px solid var(--q-sixth);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.flow-step-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--q-accent);
  transform: translateY(-2px);
}

.flow-step-card.disabled {
  opacity: 0.5;
  pointer-events: none;
  filter: grayscale(0.8);
}

.step-indicator {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(var(--q-accent-rgb), 0.2);
  color: var(--q-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}
:deep(.q-field--outlined .q-field__control):before {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined .q-field__control):after {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined.q-field--focused .q-field__control):after {
  border-color: var(--q-accent) !important;
  border-width: 1px !important;
}
</style>
