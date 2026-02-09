<template>
  <div class="q-mt-lg q-pl-md row justify-center full-width">
    <div class="full-width">
      <q-card class="bg-secondary border-light q-pa-md">
        <div class="row items-center q-mb-md">
          <q-icon name="auto_fix_high" color="purple-4" size="md" class="q-mr-sm" />
          <div class="text-h6 text-white">{{ $t('smartExtractionTitle') }}</div>
        </div>

        <q-toggle
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          color="purple-4"
          :label="$t('enableSmartExtraction')"
          class="text-white q-mb-md"
        />

        <q-banner v-if="modelValue" rounded class="bg-purple-1 text-purple-9 q-mb-md">
          <template v-slot:avatar>
            <q-icon name="psychology" color="purple-9" size="md" />
          </template>
          <div class="text-weight-bold q-mb-xs">{{ $t('aiContextEnhancement') }}</div>
          <div class="text-caption">
            {{ $t('smartExtractionIntro') }}
            <ul class="q-my-sm q-pl-md">
              <li>
                <strong>{{ $t('smartExtractionTitleLabel') }}</strong
                >: {{ $t('smartExtractionTitleDesc') }}
              </li>
              <li>
                <strong>{{ $t('smartExtractionSummaryLabel') }}</strong
                >: {{ $t('smartExtractionSummaryDesc') }}
              </li>
              <li>
                <strong>{{ $t('smartExtractionQuestionsLabel') }}</strong
                >: {{ $t('smartExtractionQuestionsDesc') }}
              </li>
            </ul>
            ⚠️ <strong>{{ $t('smartExtractionTradeoff') }}</strong
            >: {{ $t('smartExtractionTradeoffDesc') }}
          </div>
        </q-banner>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean;
}>();

defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
}>();
</script>
