<template>
  <q-card flat bordered class="text-grey-5 column q-ma-sm bg-primary" style="height: 500px">
    <q-card-section class="q-py-sm row items-center justify-between border-bottom">
      <div class="text-subtitle2">Traffic Log</div>
      <div class="row q-gutter-x-sm">
        <q-toggle
          v-model="autoScroll"
          dense
          color="accent"
          label="Auto-scroll"
          left-label
          class="text-caption"
          size="xs"
        />
        <q-btn flat dense round icon="delete" size="sm" @click="$emit('clear')" />
      </div>
    </q-card-section>

    <q-card-section class="col q-pt-md q-pl-none q-pr-none relative-position">
      <q-virtual-scroll
        ref="scrollRef"
        :items="logs"
        separator
        class="full-height no-scrollbar"
        v-slot="{ item, index }"
      >
        <q-item :key="index" dense class="q-py-xs">
          <q-item-section>
            <q-item-label class="text-caption text-weight-bold row justify-between">
              <span :class="getTypeColor(item.type)">{{ item.type }}</span>
              <span class="text-grey-6">{{ formatTime(item.timestamp) }}</span>
            </q-item-label>
            <q-item-label
              caption
              class="text-grey-5 code-font"
              style="white-space: pre-wrap; word-break: break-all"
            >
              {{ JSON.stringify(item.payload) }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-virtual-scroll>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { QVirtualScroll } from 'quasar';

export interface TrafficParams {
  type: string;
  payload: unknown;
  timestamp: number;
}

const props = defineProps<{
  logs: TrafficParams[];
}>();

defineEmits(['clear']);

const scrollRef = ref<QVirtualScroll | null>(null);
const autoScroll = ref(true);

watch(
  () => props.logs.length,
  () => {
    if (autoScroll.value && scrollRef.value) {
      void nextTick(() => {
        scrollRef.value?.scrollTo(props.logs.length - 1);
      });
    }
  },
);

function formatTime(ts: number) {
  return (
    new Date(ts).toLocaleTimeString() +
    '.' +
    new Date(ts).getMilliseconds().toString().padStart(3, '0')
  );
}

function getTypeColor(type: string) {
  if (type.includes('ERROR') || type.includes('fail')) return 'text-negative';
  if (type.includes('PROGRESS')) return 'text-accent';
  if (type.includes('STATUS')) return 'text-info';
  return 'text-white';
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid var(--q-third);
}
.code-font {
  font-family: monospace;
  font-size: 11px;
}

/* Hide scrollbar for Chrome, Safari and Opera */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbar for IE, Edge and Firefox */
.no-scrollbar {
  -ms-overflow-style: none; /* IE and Edge */
  scrollbar-width: none; /* Firefox */
}
</style>
