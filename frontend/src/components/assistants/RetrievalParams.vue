<template>
  <div class="retrieval-params text-main">
    <div v-if="!hideTitle" class="text-subtitle2 q-mb-sm">
      {{ t('retrievalStrategy') }}
    </div>
    <div class="bg-primary q-pa-sm">
      <div class="q-pt-sm">
        <q-input
          v-model.number="config.top_k_retrieval"
          type="number"
          :label="t('topKRetrieval')"
          :hint="t('topKRetrievalHint')"
          outlined
          dense
          bg-color="secondary"
          input-class="text-main"
          label-color="sub"
          class="q-mb-lg"
        />
      </div>

      <!-- Vector Similarity Cutoff -->
      <div class="q-pa-sm q-mb-lg bg-secondary" style="border: 1px solid var(--q-sixth)">
        <div class="q-mb-xs">
          {{ t('similarityCutoff') }} ({{ config.retrieval_similarity_cutoff ?? 0.5 }})
        </div>
        <q-slider
          v-model="config.retrieval_similarity_cutoff"
          :min="0.0"
          :max="1.0"
          :step="0.05"
          label
          label-always
          color="accent"
        />
        <div class="q-pl-sm">
          {{ t('similarityCutoffHint') }}
        </div>
      </div>

      <q-toggle
        v-model="config.use_reranker"
        :label="t('enableReranking')"
        color="accent"
        size="xs"
      >
        <q-tooltip>{{ t('rerankTooltip') }}</q-tooltip>
      </q-toggle>

      <div v-if="config.use_reranker" class="q-pa-sm q-gutter-y-md q-mt-xs">
        <!-- Similarity Cutoff -->
        <div class="q-pa-sm bg-secondary" style="border: 1px solid var(--q-sixth)">
          <div class="q-mb-xs">{{ t('similarityCutoff') }} ({{ config.similarity_cutoff }})</div>
          <q-slider
            v-model="config.similarity_cutoff"
            :min="0.0"
            :max="1.0"
            :step="0.05"
            label
            label-always
            color="accent"
          />
          <div class="q-pl-sm">
            {{ t('similarityCutoffHint') }}
          </div>
        </div>

        <div class="row q-col-gutter-md q-mt-xs">
          <div class="col-12 col-sm-6">
            <q-input
              v-model.number="config.top_n_rerank"
              type="number"
              :label="t('topNRerank')"
              :hint="t('topNRerankHint')"
              outlined
              dense
              bg-color="secondary"
              input-class="text-main"
              label-color="sub"
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
import type { Assistant } from 'src/services/assistantService';

defineOptions({
  name: 'RetrievalParams',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
  hideTitle?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Partial<Assistant>): void;
}>();

const { t } = useI18n();

const config = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});
</script>

<style scoped>
.bg-secondary {
  border-radius: 8px;
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
