<template>
  <div class="create-assistant-stepper">
    <q-stepper
      v-model="step"
      ref="stepper"
      animated
      header-nav
      active-color="accent"
      done-color="positive"
      class="bg-transparent"
      flat
    >
      <!-- Etape 1 : Identité & Rôle -->
      <q-step
        :name="1"
        :title="$t('wizard.step1Title')"
        :caption="$t('wizard.step1Caption')"
        icon="face"
        :done="step > 1"
        class="bg-transparent"
      >
        <q-card flat class="q-pa-md bg-transparent">
          <div class="text-h6 q-mb-md">{{ $t('wizard.step1Heading') }}</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <q-input
                v-model="form.identity.name"
                :label="$t('wizard.nameLabel')"
                standout
                outlined
                bg-color="secondary"
                :rules="[(val) => (val && val.length > 0) || $t('wizard.nameRequired')]"
                :hint="$t('wizard.nameHint')"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model="form.identity.targetUser"
                :label="$t('wizard.targetLabel')"
                standout
                outlined
                bg-color="secondary"
                :hint="$t('wizard.targetHint')"
              />
            </div>
            <div class="col-12">
              <q-input
                v-model="form.identity.role"
                :label="$t('wizard.roleLabel')"
                type="textarea"
                standout
                outlined
                bg-color="secondary"
                rows="3"
                :hint="$t('wizard.roleHint')"
              />
            </div>
          </div>
        </q-card>

        <q-stepper-navigation>
          <div class="row justify-end">
            <q-btn
              @click="nextStep"
              color="accent"
              :label="$t('wizard.btnNext')"
              unelevated
              :disable="!isStep1Valid"
              text-color="grey-3"
            />
          </div>
        </q-stepper-navigation>
      </q-step>

      <!-- Etape 2 : La Mission -->
      <q-step
        :name="2"
        :title="$t('wizard.step2Title')"
        :caption="$t('wizard.step2Caption')"
        icon="psychology"
        :done="step > 2"
        class="bg-transparent"
      >
        <q-card flat class="q-pa-md bg-transparent">
          <div class="text-h6 q-mb-md">{{ $t('wizard.step2Heading') }}</div>
          <div class="column q-gutter-y-md">
            <q-input
              v-model="form.mission.objective"
              :label="$t('wizard.objectiveLabel')"
              type="textarea"
              standout
              outlined
              bg-color="secondary"
              rows="4"
              :rules="[(val) => (val && val.length > 0) || $t('wizard.objectiveRequired')]"
              :hint="$t('wizard.objectiveHint')"
            />

            <div class="q-pa-sm rounded-borders border-grey">
              <div class="text-subtitle2 q-mb-sm">
                {{ $t('wizard.ragBehaviorLabel') }}
              </div>
              <q-option-group
                v-model="form.mission.ragBehavior"
                :options="ragOptions"
                inline
                class="text-main"
              />
            </div>
          </div>
        </q-card>

        <q-stepper-navigation>
          <div class="row justify-between">
            <q-btn flat @click="prevStep" :label="$t('wizard.btnPrev')" />
            <q-btn
              @click="nextStep"
              color="accent"
              :label="$t('wizard.btnNext')"
              unelevated
              :disable="!isStep2Valid"
            />
          </div>
        </q-stepper-navigation>
      </q-step>

      <!-- Etape 3 : Ton & Style -->
      <q-step
        :name="3"
        :title="$t('wizard.step3Title')"
        :caption="$t('wizard.step3Caption')"
        icon="record_voice_over"
        :done="step > 3"
        class="bg-transparent"
      >
        <q-card flat class="q-pa-md bg-transparent">
          <div class="text-h6 q-mb-md">{{ $t('wizard.step3Heading') }}</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.style.tone"
                :options="toneOptions"
                :label="$t('wizard.toneLabel')"
                standout
                outlined
                bg-color="secondary"
                :hint="$t('wizard.toneHint')"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.style.language"
                :options="languageOptions"
                :label="$t('wizard.languageLabel')"
                standout
                outlined
                bg-color="secondary"
                :hint="$t('wizard.languageHint')"
              />
            </div>
            <div class="col-12">
              <q-input
                v-model="form.style.format"
                :label="$t('wizard.formatLabel')"
                standout
                outlined
                bg-color="secondary"
                :hint="$t('wizard.formatHint')"
              />
            </div>
          </div>
        </q-card>

        <q-stepper-navigation>
          <div class="row justify-between">
            <q-btn flat @click="prevStep" :label="$t('wizard.btnPrev')" />
            <q-btn @click="nextStep" color="accent" :label="$t('wizard.btnNext')" unelevated />
          </div>
        </q-stepper-navigation>
      </q-step>

      <!-- Etape 4 : Garde-fous -->
      <q-step
        :name="4"
        :title="$t('wizard.step4Title')"
        :caption="$t('wizard.step4Caption')"
        icon="security"
        :done="step > 4"
        class="bg-transparent"
      >
        <q-card flat class="q-pa-md bg-transparent">
          <div class="text-h6 q-mb-md">{{ $t('wizard.step4Heading') }}</div>
          <div class="column q-gutter-y-md">
            <q-select
              v-model="form.safety.taboos"
              :label="$t('wizard.taboosLabel')"
              standout
              outlined
              bg-color="secondary"
              use-input
              use-chips
              multiple
              hide-dropdown-icon
              input-debounce="0"
              new-value-mode="add-unique"
              :hint="$t('wizard.taboosHint')"
            />

            <q-input
              v-model="form.safety.securityRules"
              :label="$t('wizard.securityRulesLabel')"
              type="textarea"
              standout
              outlined
              bg-color="secondary"
              rows="3"
              :hint="$t('wizard.securityRulesHint')"
            />
          </div>
        </q-card>

        <q-stepper-navigation>
          <div class="row justify-between">
            <q-btn flat color="grey-7" @click="prevStep" :label="$t('wizard.btnPrev')" />
            <q-btn
              @click="submit"
              color="positive"
              :label="$t('wizard.btnGenerate')"
              icon="auto_awesome"
              unelevated
              text-color="white"
            />
          </div>
        </q-stepper-navigation>
      </q-step>
    </q-stepper>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const emit = defineEmits(['submit']);
const { t } = useI18n();

interface QStepper {
  next: () => void;
  previous: () => void;
}

const step = ref(1);
const stepper = ref<QStepper | null>(null);

const form = ref({
  identity: { name: '', role: '', targetUser: '' },
  mission: {
    objective: '',
    ragBehavior: 'strict',
  },
  style: {
    tone: 'Professionnel',
    format: '',
    language: 'fr-CA',
  },
  safety: {
    taboos: [],
    securityRules: '',
  },
});

// Options
const ragOptions = computed(() => [
  { label: t('wizard.ragStrict'), value: 'strict', color: 'accent' }, // Changed color to accent
  { label: t('wizard.ragFlexible'), value: 'flexible', color: 'positive' }, // Changed color to positive/secondary
]);

const toneOptions = ['Professionnel', 'Amical', 'Technique', 'Concis', 'Explicatif'];

const languageOptions = ['Français (Québec)', 'Anglais', 'Auto-Detect'];

// Validation Computed Props
const isStep1Valid = computed(() => {
  return !!form.value.identity.name && form.value.identity.name.trim().length > 0;
});

const isStep2Valid = computed(() => {
  return !!form.value.mission.objective && form.value.mission.objective.trim().length > 0;
});

// Navigation Functions
function nextStep() {
  stepper.value?.next();
}

function prevStep() {
  stepper.value?.previous();
}

function submit() {
  emit('submit', form.value);
}
</script>

<style scoped>
.create-assistant-stepper {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}
</style>
