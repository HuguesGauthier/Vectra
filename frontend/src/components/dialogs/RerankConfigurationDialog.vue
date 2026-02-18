<template>
  <q-dialog v-model="isOpen">
    <q-card class="bg-primary" style="min-width: 500px">
      <q-card-section class="row items-center q-pb-none bg-secondary">
        <div class="text-h6">{{ providerName }} {{ $t('configuration') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-form @submit="handleSave" class="column q-gutter-y-md">
        <q-card-section class="q-pt-md">
          <!-- Hidden username to satisfy browser heuristics for password forms -->
          <input
            type="text"
            name="username"
            autocomplete="username"
            style="display: none; opacity: 0; position: absolute; left: -9999px"
            tabindex="-1"
          />

          <div class="column q-gutter-y-md">
            <!-- Cohere Configuration -->
            <template v-if="providerId === 'cohere'">
              <q-input
                v-model="internalModels.cohere_api_key"
                :label="$t('apiKey')"
                outlined
                dense
                type="password"
                autocomplete="new-password"
              />
              <div class="text-caption text-grey-6">
                {{ $t('cohereRerankDesc') || 'Recommended for highest precision.' }}
              </div>
            </template>

            <!-- Local Configuration -->
            <template v-if="providerId === 'local'">
              <q-input
                v-model="internalModels.local_rerank_model"
                :label="$t('modelName')"
                outlined
                dense
                hint="ex. BAAI/bge-reranker-base"
              />
              <div class="text-caption text-grey-6">
                {{ $t('localRerankDesc') || 'Runs privately on your CPU using FastEmbed.' }}
              </div>
            </template>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="bg-secondary text-primary">
          <q-btn flat :label="$t('cancel')" v-close-popup color="grey-7" />
          <q-btn flat :label="$t('save')" type="submit" color="accent" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue';

const props = defineProps({
  providerId: {
    type: String,
    required: true,
  },
  providerName: {
    type: String,
    default: '',
  },
  models: {
    type: Object as PropType<Record<string, string>>,
    default: () => ({}),
  },
});

const emit = defineEmits(['update:isOpen', 'save']);
const isOpen = defineModel<boolean>('isOpen', { default: false });

const internalModels = ref<Record<string, string>>({});

watch(
  () => props.models,
  (newVal) => {
    internalModels.value = { ...newVal };
  },
  { immediate: true, deep: true },
);

function handleSave() {
  emit('save', internalModels.value);
  isOpen.value = false;
}
</script>
