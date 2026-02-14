<template>
  <div class="column full-height">
    <q-stepper
      v-model="step"
      vertical
      color="accent"
      active-color="accent"
      done-color="positive"
      animated
      flat
      class="bg-transparent"
    >
      <!-- Step 1: General Info -->
      <q-step :name="1" :title="$t('generalInfo')" icon="edit" :done="step > 1">
        <q-form ref="step1Form" @submit="step = 2">
          <q-input
            v-model="formData.name"
            :label="$t('name')"
            :hint="$t('connectorNameHint')"
            outlined
            color="accent"
            bg-color="secondary"
            lazy-rules
            autofocus
            :rules="[(val) => !!val || $t('fieldRequired')]"
            class="q-mb-md"
          />

          <q-input
            v-model="formData.description"
            :label="$t('description')"
            :hint="$t('connectorDescriptionHint')"
            type="textarea"
            outlined
            color="accent"
            bg-color="secondary"
            autogrow
            class="q-mb-md"
          />
        </q-form>
      </q-step>

      <!-- Step 2: Connection Details -->
      <q-step :name="2" :title="$t('connectionDetails')" icon="dns" :done="step > 2">
        <q-form ref="step2Form" @submit="onSubmit">
          <q-input
            v-model="formData.host"
            :label="$t('labelHostSql')"
            :hint="$t('labelHostHint')"
            outlined
            color="accent"
            bg-color="secondary"
            lazy-rules
            :rules="[(val) => !!val || $t('fieldRequired')]"
            class="q-mb-md"
          />

          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-8">
              <q-input
                v-model="formData.database"
                :label="$t('labelDatabaseName')"
                :hint="$t('labelDatabaseHint')"
                outlined
                color="accent"
                bg-color="secondary"
                lazy-rules
                :rules="[(val) => !!val || $t('fieldRequired')]"
              />
            </div>
            <div class="col-4">
              <q-input
                v-model.number="formData.port"
                :label="$t('labelPort')"
                :hint="$t('labelPortHint')"
                type="number"
                outlined
                color="accent"
                bg-color="secondary"
                lazy-rules
                :rules="[(val) => !!val || $t('fieldRequired')]"
              />
            </div>
          </div>

          <q-input
            v-model="formData.schema"
            :label="$t('labelSchema')"
            :hint="$t('labelSchemaHint')"
            outlined
            color="accent"
            bg-color="secondary"
            lazy-rules
            :rules="[(val) => !!val || $t('fieldRequired')]"
            class="q-mb-md"
          />

          <q-input
            v-model="formData.user"
            :label="$t('labelUserSql')"
            :hint="$t('labelUserHint')"
            outlined
            color="accent"
            bg-color="secondary"
            lazy-rules
            :rules="[(val) => !!val || $t('fieldRequired')]"
            class="q-mb-md"
          />

          <q-input
            v-model="formData.password"
            :label="$t('labelPassword')"
            :hint="$t('labelPasswordHint')"
            type="password"
            outlined
            color="accent"
            bg-color="secondary"
            lazy-rules
            :rules="[(val) => !!val || $t('fieldRequired')]"
            class="q-mb-lg"
          />

          <div v-if="testResult !== 'none'" class="row items-center q-gutter-sm">
            <q-icon v-if="testResult === 'success'" name="check_circle" color="positive" size="sm">
              <q-tooltip>{{ $t('connectionSuccess') }}</q-tooltip>
            </q-icon>
            <q-icon v-if="testResult === 'failed'" name="error" color="negative" size="sm">
              <q-tooltip>{{ testErrorMessage || $t('connectionFailed') }}</q-tooltip>
            </q-icon>
            <span v-if="testResult === 'success'" class="text-positive text-caption">{{
              $t('connectionSuccess')
            }}</span>
            <span v-if="testResult === 'failed'" class="text-negative text-caption">{{
              $t('connectionFailed')
            }}</span>
          </div>
        </q-form>
      </q-step>
    </q-stepper>

    <!-- Hidden Fields for logic -->
    <q-select
      v-if="!hideSchedule"
      v-model="formData.schedule_type"
      class="hidden"
      :options="scheduleOptions"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { Connector } from 'src/models/Connector';
import type { ScheduleType } from 'src/models/enums';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { useQuasar } from 'quasar';

const { t } = useI18n();
const $q = useQuasar();

// --- PROPS & EMITS ---
const props = defineProps({
  hideSchedule: { type: Boolean, default: false },
  hideActions: { type: Boolean, default: false },
});

const data = defineModel<Connector>('data');
const emit = defineEmits(['save']);

// --- STATE ---
const step = ref(1);
const step1Form = ref();
const step2Form = ref();
const isTesting = ref(false);
const testResult = ref<'none' | 'success' | 'failed'>('none');
const testErrorMessage = ref('');

const formData = ref({
  // Step 1
  name: data.value?.name || '',
  description: data.value?.description || '',

  // Step 2
  host: (data.value?.configuration?.host as string) || '',
  port: (data.value?.configuration?.port as number) || 1433,
  database: (data.value?.configuration?.database as string) || '',
  schema: (data.value?.configuration?.schema as string) || 'vectra',
  user: (data.value?.configuration?.user as string) || '',
  password: (data.value?.configuration?.password as string) || '',
  schedule_type: (data.value?.schedule_type as string) || 'manual',
});

// Watch for changes and sync back to parent data model
watch(
  formData,
  (val) => {
    // Reset test result on change
    testResult.value = 'none';
    testErrorMessage.value = '';

    if (!data.value) return;

    // Sync Step 1
    data.value.name = val.name;
    data.value.description = val.description;

    // Sync Step 2
    if (!data.value.configuration) data.value.configuration = {};
    data.value.configuration.host = val.host;
    data.value.configuration.port = val.port;
    data.value.configuration.database = val.database;
    data.value.configuration.schema = val.schema;
    data.value.configuration.user = val.user;
    data.value.configuration.password = val.password;

    if (!props.hideSchedule) {
      data.value.schedule_type = val.schedule_type as ScheduleType;
    }
  },
  { deep: true },
);

// --- COMPUTED ---
const scheduleOptions = computed(() => [
  { label: t('scheduleManual'), value: 'manual' },
  { label: t('scheduleDaily'), value: 'daily' },
  { label: t('scheduleWeekly'), value: 'weekly' },
  { label: t('scheduleMonthly'), value: 'monthly' },
]);

// --- FUNCTIONS ---
async function onTestConnection() {
  const valid = await step2Form.value?.validate();
  if (!valid) return;

  isTesting.value = true;
  testResult.value = 'none';

  try {
    const response = await api.post('/connectors/test-connection', {
      connector_type: 'sql',
      configuration: {
        host: formData.value.host,
        port: formData.value.port,
        database: formData.value.database,
        schema: formData.value.schema,
        user: formData.value.user,
        password: formData.value.password,
      },
    });

    if (response.data.success) {
      testResult.value = 'success';
      $q.notify({
        type: 'positive',
        message: t('connectionSuccess'),
        position: 'top',
        timeout: 2000,
      });
    } else {
      testResult.value = 'failed';
      testErrorMessage.value = response.data.message;
      $q.notify({
        type: 'negative',
        message: t('connectionFailed') + ': ' + response.data.message,
        position: 'top',
        timeout: 5000,
        actions: [{ icon: 'close', color: 'white' }],
      });
    }
  } catch (error: unknown) {
    const axiosError = error as AxiosError<{ message?: string }>;
    testResult.value = 'failed';
    const msg = axiosError.response?.data?.message || axiosError.message || t('unknownError');
    testErrorMessage.value = msg;
    $q.notify({
      type: 'negative',
      message: t('connectionFailed') + ': ' + msg,
      position: 'top',
      timeout: 5000,
      actions: [{ icon: 'close', color: 'white' }],
    });
  } finally {
    isTesting.value = false;
  }
}

function onSubmit() {
  emit('save', formData.value);
}

// Expose submit for the Parent Stepper to call via ref
async function submit() {
  // If we are on Step 1, force validation and move to Step 2 if valid
  if (step.value === 1) {
    const s1Valid = await step1Form.value?.validate();
    if (!s1Valid) return false;
    step.value = 2;
    // We return false to parent because we just moved to step 2 locally,
    // we don't want parent to proceed to ITS next step yet.
    // BUT, the parent AddConnectorStepper expects `submit()` to return TRUE
    // when the WHOLE form is valid and ready to move to parent's next step.

    // So if user clicks "Next" on parent stepper while on Step 1 of internal stepper:
    // We should probably block and Auto-Advance internal stepper.
    // Let's return false so parent doesn't advance, but we advanced internally.
    return false;
  }

  // If we are on Step 2, validate it
  if (step.value === 2) {
    const s2Valid = await step2Form.value?.validate();
    if (!s2Valid) return false;

    if (testResult.value !== 'success') {
      $q.notify({
        type: 'warning',
        message: t('testConnectionRequired'),
        position: 'top',
      });
      return false;
    }

    return true;
  }

  return false;
}

function back() {
  if (step.value === 2) {
    step.value = 1;
    return true; // We handled the back action locally
  }
  return false; // We are at step 1, parent should handle back
}

defineExpose({ submit, back, formData, onTestConnection, isTesting, testResult, step });
</script>

<style scoped>
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
