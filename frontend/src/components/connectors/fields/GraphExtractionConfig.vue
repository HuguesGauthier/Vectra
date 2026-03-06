<template>
  <div class="q-mt-lg q-pl-md row justify-center full-width">
    <div class="full-width">
      <q-card class="bg-secondary border-light q-pa-md">
        <div class="row items-center q-mb-md">
          <q-icon name="hub" color="blue-4" size="md" class="q-mr-sm" />
          <div class="text-h6 text-white">{{ $t('graphExtractionTitle') }}</div>
        </div>

        <q-toggle
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          color="blue-4"
          :label="$t('enableGraphExtraction')"
          class="text-white q-mb-md"
        />

        <q-banner v-if="modelValue" rounded class="bg-blue-1 text-blue-9 q-mb-md">
          <template v-slot:avatar>
            <q-icon name="account_tree" color="blue-9" size="md" />
          </template>
          <div class="text-weight-bold q-mb-xs">Neo4j Graph RAG</div>
          <div class="text-caption">
            {{ $t('graphExtractionIntro') }}
            <ul class="q-my-sm q-pl-md">
              <li>
                <strong>{{ $t('graphExtractionEntitiesLabel') }}</strong
                >: {{ $t('graphExtractionEntitiesDesc') }}
              </li>
              <li>
                <strong>{{ $t('graphExtractionRelationshipsLabel') }}</strong
                >: {{ $t('graphExtractionRelationshipsDesc') }}
              </li>
            </ul>
            ⚠️ <strong>{{ $t('graphExtractionTradeoff') }}</strong
            >: {{ $t('graphExtractionTradeoffDesc') }}
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
