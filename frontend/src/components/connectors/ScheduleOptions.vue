<template>
  <div class="row justify-center max-width-container">
    <!-- Schedule Options Grid -->
    <div v-for="sched in scheduleOptions" :key="sched.id" class="col-12 col-sm-6 col-md-3 q-pa-sm">
      <q-card
        class="selection-card full-height q-pa-sm"
        :class="{
          selected: selectedSchedule === sched.id,
          'cursor-pointer': !isScheduleDisabled(sched.id),
        }"
        v-ripple="!isScheduleDisabled(sched.id)"
        @click="handleScheduleSelect(sched.id)"
        :style="isScheduleDisabled(sched.id) ? 'opacity: 0.5; cursor: not-allowed' : ''"
      >
        <q-card-section class="column items-center text-center">
          <q-icon :name="sched.icon" size="48px" class="q-mb-md" :color="sched.color" />
          <div class="text-h6 text-white">{{ sched.name }}</div>
          <div class="text-caption text-grey-5 q-mt-sm">{{ sched.description }}</div>
        </q-card-section>
        <div v-if="selectedSchedule === sched.id" class="selected-overlay">
          <q-icon name="check_circle" color="accent" size="32px" />
        </div>

        <AppTooltip v-if="isScheduleDisabled(sched.id)">
          {{ $t('manualOnlyForLocalFiles') }}
        </AppTooltip>

        <div class="q-mt-sm" v-if="selectedSchedule === sched.id && sched.id !== 'manual'">
          <q-btn
            outline
            size="sm"
            color="accent"
            label="Configure"
            icon="settings"
            @click.stop="openConfigDialog"
          />
        </div>
      </q-card>
    </div>

    <!-- Schedule Configuration Dialog -->
    <q-dialog v-model="configDialog">
      <q-card class="bg-secondary text-white" style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">
            <q-icon name="settings_suggest" size="sm" class="q-mr-sm" />
            {{ $t('configureSchedule') || 'Configure Schedule' }}
          </div>
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-md">
            <!-- Hourly: Minute Selection -->
            <div v-if="selectedSchedule === 'hourly'" class="col-12">
              <q-input
                v-model.number="configMinute"
                type="number"
                label="Minute (0-59)"
                dark
                outlined
                :rules="[(val) => (val >= 0 && val <= 59) || 'Invalid minute']"
              />
            </div>

            <!-- Daily/Weekly/Monthly: Hour Selection -->
            <div v-if="['daily', 'weekly', 'monthly'].includes(selectedSchedule)" class="col-12">
              <q-input
                v-model="configTime"
                mask="time"
                :rules="['time']"
                label="Time (HH:MM)"
                dark
                outlined
              >
                <template v-slot:append>
                  <q-icon name="access_time" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-time v-model="configTime">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-time>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>

            <!-- Weekly: Day Selection -->
            <div v-if="selectedSchedule === 'weekly'" class="col-12">
              <q-select
                v-model="configDayWeek"
                :options="daysOfWeek"
                option-value="value"
                option-label="label"
                emit-value
                map-options
                label="Day of Week"
                dark
                outlined
              />
            </div>

            <!-- Monthly: Day Selection -->
            <div v-if="selectedSchedule === 'monthly'" class="col-12">
              <q-input
                v-model.number="configDayMonth"
                type="number"
                label="Day of Month (1-31)"
                dark
                outlined
                :rules="[(val) => (val >= 1 && val <= 31) || 'Invalid day']"
              />
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
          <q-btn label="Done" color="accent" v-close-popup @click="applyConfig" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import { getScheduleConfigFromUiType, parseCronExpression } from 'src/models/Connector';

defineOptions({
  name: 'ScheduleOptions',
});

const props = defineProps<{
  modelValue?: string | undefined; // The cron string
  connectorType?: string | undefined;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | undefined): void;
}>();

const { t } = useI18n();

// --- STATE ---
const selectedSchedule = ref<string>('manual');
const configDialog = ref(false);

const configMinute = ref(0);
const configHour = ref(0);
const configDayWeek = ref(1);
const configDayMonth = ref(1);
const configTime = ref('00:00');

// --- COMPUTED ---
const scheduleOptions = computed(() => [
  {
    id: 'manual',
    name: t('scheduleManual'),
    description: t('scheduleManualDesc'),
    icon: 'touch_app',
    color: 'grey-5',
  },
  {
    id: 'hourly',
    name: t('Hourly'),
    description: t('Every hour'),
    icon: 'update',
    color: 'teal-5',
  },
  {
    id: 'daily',
    name: t('scheduleDaily'),
    description: t('scheduleDailyDesc'),
    icon: 'today',
    color: 'blue-5',
  },
  {
    id: 'weekly',
    name: t('scheduleWeekly'),
    description: t('scheduleWeeklyDesc'),
    icon: 'date_range',
    color: 'purple-5',
  },
  {
    id: 'monthly',
    name: t('scheduleMonthly'),
    description: t('scheduleMonthlyDesc'),
    icon: 'event',
    color: 'orange-5',
  },
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

// --- FUNCTIONS ---
function isScheduleDisabled(schedId: string) {
  if (props.connectorType === 'local_file' && schedId !== 'manual') {
    return true;
  }
  return false;
}

function handleScheduleSelect(schedId: string) {
  if (isScheduleDisabled(schedId)) return;
  selectedSchedule.value = schedId;

  if (schedId === 'manual') {
    emit('update:modelValue', undefined);
  } else {
    // Open config to let user refine, but also emit default "safe" value immediately?
    // Or wait for done?
    // Let's open config dialog.
    configDialog.value = true;
    // Apply current defaults to emit immediately or wait?
    // Better to have valid state. Let's apply default config immediately so the UI reflects "Hourly" even if they don't change minute.
    applyConfig();
  }
}

function openConfigDialog() {
  configDialog.value = true;
}

function applyConfig() {
  const result = getScheduleConfigFromUiType(selectedSchedule.value, {
    minute: configMinute.value,
    hour: configHour.value,
    dayWeek: configDayWeek.value,
    dayMonth: configDayMonth.value,
  });
  emit('update:modelValue', result.schedule_cron);
}

// Watchers and parsing
watch(
  () => props.modelValue,
  (val) => {
    parseAndSync(val);
  },
  { immediate: true },
);

function parseAndSync(cron?: string | null) {
  if (!cron) {
    if (selectedSchedule.value !== 'manual') {
      // Only reset if we are not already manual, to avoid wiping transient user selection if they just clicked it?
      // Actually prop is source of truth.
      selectedSchedule.value = 'manual';
    }
    return;
  }

  const parsed = parseCronExpression(cron);
  selectedSchedule.value = parsed.type;
  configMinute.value = parsed.minute;
  configHour.value = parsed.hour;
  configDayWeek.value = parsed.dayWeek;
  configDayMonth.value = parsed.dayMonth;

  // Sync time string
  const h = String(parsed.hour).padStart(2, '0');
  const m = String(parsed.minute).padStart(2, '0');
  configTime.value = `${h}:${m}`;
}

watch(configTime, (val) => {
  if (val) {
    const [h, m] = val.split(':').map((x) => parseInt(x, 10));
    configHour.value = h || 0;
    configMinute.value = m || 0;
  }
});
</script>

<style scoped>
.selection-card {
  transition: all 0.2s ease-in-out;
  border: 2px solid transparent;
  background: rgba(255, 255, 255, 0.05); /* slightly lighter than bg-primary */
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.selection-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.08); /* hover state */
  border-color: rgba(255, 255, 255, 0.1);
}

.selection-card.selected {
  border-color: var(--q-utils-info); /* Use accent color */
  background: rgba(var(--q-accent-rgb), 0.15) !important; /* reliable accent tint */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.selected-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  background: radial-gradient(circle, rgba(0, 0, 0, 0.5) 0%, transparent 70%);
  border-radius: 50%;
}
</style>
