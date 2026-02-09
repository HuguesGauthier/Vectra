<template>
  <q-dialog v-model="isOpen">
    <q-card class="bg-primary text-white" style="min-width: 500px">
      <q-card-section>
        <div class="text-h6">
          {{ $t('advancedIndexingSettings') }}
        </div>
        <div class="text-caption text-grey-5">
          {{ $t('advancedIndexingDesc') }}
        </div>
      </q-card-section>

      <q-card-section class="q-pa-lg bg-primary">
        <div class="row q-col-gutter-lg">
          <!-- Chunk Size -->
          <div class="col-12">
            <q-card dark class="q-pa-xs param-card">
              <div class="text-caption text-grey-5 q-ml-xs row justify-between">
                <span>{{ $t('chunkSize') }}</span>
                <span class="text-accent text-weight-bold">{{ localChunkSize }}</span>
              </div>
              <q-slider
                :model-value="localChunkSize"
                @update:model-value="onSizeChange"
                :min="150"
                :max="8192"
                :step="1"
                label
                color="accent"
                dark
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption text-grey-5 q-mb-sm q-pl-sm">
              {{ $t('chunkSizeHint') }}
            </div>
          </div>

          <!-- Chunk Overlap -->
          <div class="col-12">
            <q-card dark class="q-pa-xs param-card">
              <div class="text-caption text-grey-5 q-ml-xs row justify-between">
                <span>{{ $t('chunkOverlap') }}</span>
                <span class="text-accent text-weight-bold">{{ localChunkOverlap }}</span>
              </div>
              <q-slider
                :model-value="localChunkOverlap"
                @update:model-value="onOverlapChange"
                :min="0"
                :max="8192"
                :step="1"
                label
                color="accent"
                dark
                dense
                class="q-pl-sm q-pr-sm q-pt-xs"
              />
            </q-card>
            <div class="text-caption text-grey-5 q-mb-sm q-pl-sm">
              {{ $t('chunkOverlapHint') }} (Max: {{ localChunkSize }})
            </div>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="q-pa-md bg-primary">
        <q-btn flat :label="$t('cancel')" color="grey-5" v-close-popup />
        <q-btn color="accent" :label="$t('save')" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  chunkSize?: number;
  chunkOverlap?: number;
}>();

const emit = defineEmits<{
  (e: 'update', payload: { chunkSize: number; chunkOverlap: number }): void;
}>();

const isOpen = defineModel<boolean>('isOpen', { required: true });

const localChunkSize = ref(300);
const localChunkOverlap = ref(30);
// Store the ratio (overlap / size) to maintain it when size changes
const overlapRatio = ref(0.1); // Default approx 30/300

// Initialize state from props
watch(
  () => [props.chunkSize, props.chunkOverlap],
  ([newSize, newOverlap]) => {
    if (newSize) localChunkSize.value = newSize;
    if (newOverlap !== undefined) localChunkOverlap.value = newOverlap;

    // Calculate initial ratio
    if (localChunkSize.value > 0) {
      overlapRatio.value = localChunkOverlap.value / localChunkSize.value;
    }
  },
  { immediate: true },
);

// Handler for Size Slider
function onSizeChange(newVal: number | null) {
  if (newVal === null) return;
  localChunkSize.value = newVal;

  // Update overlap to keep the same ratio
  const newOverlap = Math.round(newVal * overlapRatio.value);
  // Ensure we don't exceed the new size (though ratio <= 1 should prevent this)
  localChunkOverlap.value = Math.min(newOverlap, newVal);
}

// Handler for Overlap Slider
function onOverlapChange(newVal: number | null) {
  if (newVal === null) return;
  // Clamp value to not exceed chunk size
  const safeVal = Math.min(newVal, localChunkSize.value);
  localChunkOverlap.value = safeVal;

  // User manually adjusted overlap, so we update the target ratio
  if (localChunkSize.value > 0) {
    overlapRatio.value = safeVal / localChunkSize.value;
  }
}

function save() {
  emit('update', {
    chunkSize: localChunkSize.value,
    chunkOverlap: localChunkOverlap.value,
  });
  isOpen.value = false;
}
</script>

<style scoped lang="scss">
.param-card {
  background-color: var(--q-fourth);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
</style>
