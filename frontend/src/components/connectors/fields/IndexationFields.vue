<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs">{{ $t('indexationSettings') }}</div>

    <div class="q-mb-md">
      <div class="text-caption q-mb-xs">{{ $t('embeddingProvider') }}</div>
      <AiProviderGrid
        :model-value="modelValue.ai_provider"
        @update:model-value="updateField('ai_provider', $event || '')"
        :providers="enrichedProviders"
        selectable
        compact
        grid-cols="col-12 col-sm-6"
      />
      <div v-if="disableAiProvider" class="text-caption text-warning q-mt-xs">
        <q-icon name="info" size="xs" class="q-mr-xs" />
        {{ $t('cannotChangeAfterCreation') }}
      </div>
    </div>

    <q-toggle
      v-if="showRecursive"
      :model-value="modelValue.recursive"
      @update:model-value="updateField('recursive', $event)"
      :label="$t('recursive')"
      color="positive"
      dark
    />

    <!-- Schedule Type -->
    <q-select
      :model-value="modelValue.schedule_type"
      @update:model-value="updateField('schedule_type', $event || 'manual')"
      :options="scheduleOptions"
      :label="$t('schedule')"
      dark
      standout
      emit-value
      map-options
    />

    <!-- Detailed Schedule Settings -->
    <div
      v-if="modelValue.schedule_type && modelValue.schedule_type !== 'manual'"
      class="q-pl-md q-gutter-sm border-left"
    >
      <!-- Hourly: Minute -->
      <q-input
        v-if="modelValue.schedule_type === 'hourly'"
        :model-value="modelValue.minute"
        @update:model-value="updateField('minute', parseInt(String($event)) || 0)"
        type="number"
        label="Minute (0-59)"
        dark
        outlined
        dense
        :rules="[(val) => (val >= 0 && val <= 59) || 'Invalid minute']"
      />

      <!-- Time Selection (Daily/Weekly/Monthly) -->
      <q-input
        v-if="['daily', 'weekly', 'monthly'].includes(modelValue.schedule_type)"
        :model-value="formattedTime"
        @update:model-value="updateTime"
        mask="time"
        :rules="['time']"
        label="Time (HH:MM)"
        dark
        outlined
        dense
      >
        <template v-slot:append>
          <q-icon name="access_time" class="cursor-pointer">
            <q-popup-proxy cover transition-show="scale" transition-hide="scale">
              <q-time :model-value="formattedTime" @update:model-value="updateTime">
                <div class="row items-center justify-end">
                  <q-btn v-close-popup label="Close" color="primary" flat />
                </div>
              </q-time>
            </q-popup-proxy>
          </q-icon>
        </template>
      </q-input>

      <!-- Weekly: Day of Week -->
      <q-select
        v-if="modelValue.schedule_type === 'weekly'"
        :model-value="modelValue.dayWeek"
        @update:model-value="updateField('dayWeek', $event)"
        :options="daysOfWeek"
        option-value="value"
        option-label="label"
        emit-value
        map-options
        label="Day of Week"
        dark
        outlined
        dense
      />

      <!-- Monthly: Day of Month -->
      <q-input
        v-if="modelValue.schedule_type === 'monthly'"
        :model-value="modelValue.dayMonth"
        @update:model-value="updateField('dayMonth', parseInt(String($event)) || 1)"
        type="number"
        label="Day of Month (1-31)"
        dark
        outlined
        dense
        :rules="[(val) => (val >= 1 && val <= 31) || 'Invalid day']"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAiProviders } from 'src/composables/useAiProviders';
import AiProviderGrid from 'src/components/common/AiProviderGrid.vue';

const { t } = useI18n();
const { embeddingProviderOptions } = useAiProviders();

// --- DEFINITIONS ---
export interface IndexationConfig {
  ai_provider: string;
  schedule_type: string;
  recursive?: boolean;
  minute?: number;
  hour?: number;
  dayWeek?: number;
  dayMonth?: number;
}

const props = defineProps<{
  showRecursive?: boolean;
  disableAiProvider?: boolean;
}>();

const modelValue = defineModel<IndexationConfig>({ required: true });

// --- COMPUTED ---
const scheduleOptions = computed(() => [
  { label: t('scheduleManual'), value: 'manual' },
  { label: t('Hourly'), value: 'hourly' }, // TODO: Add translation
  { label: t('scheduleDaily'), value: 'daily' },
  { label: t('scheduleWeekly'), value: 'weekly' },
  { label: t('scheduleMonthly'), value: 'monthly' },
]);

const daysOfWeek = computed(() => [
  { label: 'Sunday', value: 0 },
  { label: 'Monday', value: 1 },
  { label: 'Tuesday', value: 2 },
  { label: 'Wednesday', value: 3 },
  { label: 'Thursday', value: 4 },
  { label: 'Friday', value: 5 },
  { label: 'Saturday', value: 6 },
]);

const formattedTime = computed(() => {
  const h = String(modelValue.value.hour || 0).padStart(2, '0');
  const m = String(modelValue.value.minute || 0).padStart(2, '0');
  return `${h}:${m}`;
});

const enrichedProviders = computed(() => {
  return embeddingProviderOptions.value.map((p) => ({
    ...p,
    disabled: p.disabled || props.disableAiProvider,
  }));
});

// --- FUNCTIONS ---
function updateField(field: keyof IndexationConfig, value: string | boolean | number) {
  modelValue.value = { ...modelValue.value, [field]: value };
}

function updateTime(timeStr: string | number | null) {
  if (!timeStr || typeof timeStr !== 'string') return;
  const [h, m] = timeStr.split(':').map((x) => parseInt(x, 10));
  modelValue.value = {
    ...modelValue.value,
    hour: h || 0,
    minute: m || 0,
  };
}
</script>

<style scoped>
.border-left {
  border-left: 2px solid var(--q-grey-8);
}
</style>
