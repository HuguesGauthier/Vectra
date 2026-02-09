<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="advanced-params-card bg-primary">
      <q-card-section>
        <div class="text-h6">{{ $t('advancedLlmParameters') }}</div>
        <div class="text-caption">{{ $t('advancedLlmParametersDesc') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-lg">
          <!-- Temperature -->
          <div class="col-12">
            <q-card class="q-pa-xs" style="background-color: var(--q-secondary)">
              <div class="text-caption q-ml-xs">
                {{ $t('assistantTemperature') }}
              </div>
              <q-slider
                v-if="configuration"
                :model-value="configuration.temperature"
                @update:model-value="(val) => update('temperature', val)"
                :min="0.0"
                :max="1.0"
                :step="0.1"
                label
                color="accent"
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption q-mb-sm q-pl-sm">
              {{ $t('temperatureHint') }}
            </div>
          </div>

          <!-- Top P -->
          <div class="col-12">
            <q-card class="q-pa-xs" style="background-color: var(--q-secondary)">
              <div class="text-caption q-ml-xs">{{ $t('topP') }}</div>
              <q-slider
                v-if="configuration"
                :model-value="configuration.top_p"
                @update:model-value="(val) => update('top_p', val)"
                :min="0.0"
                :max="1.0"
                :step="0.1"
                label
                color="accent"
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption q-mb-sm q-pl-sm">
              {{ $t('topPHint') }}
            </div>
          </div>

          <!-- Max Tokens -->
          <div class="col-12">
            <q-card class="q-pa-xs" style="background-color: var(--q-secondary)">
              <div class="text-caption q-ml-xs">{{ $t('maxOutputTokens') }}</div>
              <q-slider
                v-if="configuration"
                :model-value="configuration.max_output_tokens"
                @update:model-value="(val) => update('max_output_tokens', val)"
                :min="1024"
                :max="8192"
                :step="1"
                label
                color="accent"
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption q-mb-sm q-pl-sm">
              {{ $t('maxOutputTokensHint') }}
            </div>
          </div>

          <!-- Frequency Penalty -->
          <div class="col-12">
            <q-card class="q-pa-xs" style="background-color: var(--q-secondary)">
              <div class="text-caption q-ml-xs">{{ $t('frequencyPenalty') }}</div>
              <q-slider
                v-if="configuration"
                :model-value="configuration.frequency_penalty"
                @update:model-value="(val) => update('frequency_penalty', val)"
                :min="0.0"
                :max="1.0"
                :step="0.1"
                label
                color="accent"
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption q-mb-sm q-pl-sm">
              {{ $t('frequencyPenaltyHint') }}
            </div>
          </div>

          <!-- Presence Penalty -->
          <div class="col-12">
            <q-card class="q-pa-xs" style="background-color: var(--q-secondary)">
              <div class="text-caption q-ml-xs">{{ $t('presencePenalty') }}</div>
              <q-slider
                v-if="configuration"
                :model-value="configuration.presence_penalty"
                @update:model-value="(val) => update('presence_penalty', val)"
                :min="0.0"
                :max="1.0"
                :step="0.1"
                label
                color="accent"
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption q-mb-sm q-pl-sm">
              {{ $t('presencePenaltyHint') }}
            </div>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="bg-primary">
        <q-btn flat :label="$t('close')" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
defineOptions({
  name: 'AdvancedLLMParams',
});

// Define configuration interface locally if not available globally,
// or use the one from Assistant type if possible.
// For now, strict local definition is good.
interface LLMConfiguration {
  temperature?: number;
  top_p?: number;
  max_output_tokens?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  tags?: string[];
  [key: string]: unknown;
}

const props = defineProps<{
  modelValue: boolean;
  configuration: LLMConfiguration;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'update:configuration', value: LLMConfiguration): void;
}>();

const update = (key: keyof LLMConfiguration, value: number | null) => {
  emit('update:configuration', {
    ...props.configuration,
    [key]: value,
  });
};
</script>

<style scoped lang="scss">
.advanced-params-card {
  min-width: 600px;
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
