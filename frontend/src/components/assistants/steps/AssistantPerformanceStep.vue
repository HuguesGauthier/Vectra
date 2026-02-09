<template>
  <div class="assistant-performance-step">
    <div v-if="!hideTitle" class="text-subtitle1 q-mb-sm">
      {{ t('wizard.stepPerformanceTitle') }}
    </div>
    <div class="rounded-borders q-pa-sm">
      <div class="q-pt-sm">
        <q-toggle
          v-model="config.use_semantic_cache"
          :label="t('performance.enableCache')"
          color="accent"
          size="xs"
        />
      </div>

      <div v-if="config.use_semantic_cache" class="q-pa-sm q-gutter-y-md q-mt-xs">
        <!-- Similarity Threshold -->
        <div class="q-pa-sm bg-secondary" style="border: 1px solid var(--q-sixth)">
          <div class="text-caption q-mb-xs">
            {{ t('performance.similarityThreshold') }} ({{ config.cache_similarity_threshold }})
          </div>
          <q-slider
            v-model="config.cache_similarity_threshold"
            :min="0.0"
            :max="1.0"
            :step="0.01"
            label
            label-always
            color="accent"
            dark
          />
          <div class="text-caption q-pl-sm">
            {{ t('performance.thresholdHelp') }}
          </div>
        </div>

        <!-- TTL (Seconds)-->
        <div class="col-12 q-pa-sm bg-secondary" style="border: 1px solid var(--q-sixth)">
          <div class="text-caption q-mb-xs">
            {{ t('performance.cacheTTL') }} ({{ formatDuration(config.cache_ttl_seconds) }})
          </div>
          <q-slider
            v-model="config.cache_ttl_seconds"
            :min="60"
            :max="604800"
            :step="60"
            label
            :label-value="formatDuration(config.cache_ttl_seconds)"
            color="accent"
            dark
          />
          <div class="text-caption q-pl-sm">
            {{ t('performance.ttlHelp') }}
          </div>
        </div>

        <div class="text-caption q-pa-sm bg-info text-white rounded-borders">
          <q-icon name="info" class="q-mr-xs" />
          {{ t('performance.cacheHelpResult') }}
        </div>

        <!-- Manual Invalidation (Only if assistant exists) -->
        <div v-if="config.id">
          <q-separator class="q-my-lg" />

          <div class="text-subtitle2 text-negative q-mb-sm">
            <q-icon name="warning" class="q-mr-xs" />
            {{ t('performance.dangerZone') }}
          </div>

          <div class="row items-center justify-between no-wrap q-gutter-x-md">
            <div class="text-caption col">
              {{ t('performance.purgeCacheHelp') }}
            </div>

            <q-btn
              :label="t('performance.purgeCache')"
              color="negative"
              icon="delete_sweep"
              outline
              no-caps
              dense
              class="q-px-md"
              @click="handlePurgeCache"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { useDialog } from 'src/composables/useDialog';
import { assistantService, type Assistant } from 'src/services/assistantService';

defineOptions({
  name: 'AssistantPerformanceStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Partial<Assistant>): void;
}>();

const { t } = useI18n();
const $q = useQuasar();

const config = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

function formatDuration(seconds: number | undefined): string {
  if (!seconds) return `0${t('performance.timeUnits.seconds')}`;
  if (seconds < 60) return `${seconds}${t('performance.timeUnits.seconds')}`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} ${t('performance.timeUnits.minutes')}`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24)
    return `${hours}${t('performance.timeUnits.hours')} ${
      remainingMinutes > 0 ? remainingMinutes + t('performance.timeUnits.minutes') : ''
    }`;
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return `${days}${t('performance.timeUnits.days')} ${
    remainingHours > 0 ? remainingHours + t('performance.timeUnits.hours') : ''
  }`;
}

const { confirm } = useDialog();

function handlePurgeCache() {
  if (!props.modelValue.id) return;

  confirm({
    title: t('performance.purgeConfirmTitle'),
    message: t('performance.purgeConfirmMessage'),
    confirmLabel: t('performance.purgeCache'),
    confirmColor: 'negative',
    onConfirm: () => {
      void (async () => {
        try {
          const result = await assistantService.clearCache(props.modelValue.id!);
          $q.notify({
            type: 'positive',
            message: `${t('performance.purgeSuccess')} (${result.deleted_count} items)`,
          });
        } catch (error) {
          console.error(error);
        }
      })();
    },
  });
}
</script>

<style scoped>
.bg-secondary {
  border-radius: 8px;
}
</style>
