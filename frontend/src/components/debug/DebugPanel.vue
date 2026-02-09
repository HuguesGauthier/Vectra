<template>
  <div class="column full-height">
    <div class="row items-center justify-between q-pa-sm border-bottom">
      <div class="text-subtitle1">WebSocket Inspector</div>
      <div class="row items-center q-gutter-x-sm">
        <div class="text-caption">Real-time traffic</div>
        <q-toggle
          v-model="isEnabled"
          dense
          color="accent"
          size="xs"
          left-label
          class="text-caption"
        />
      </div>
    </div>

    <!-- Stats -->
    <div class="q-pa-sm">
      <TrafficStats
        :total-messages="totalMessages"
        :messages-per-second="mps"
        :last-message-type="lastMsgType"
      />
    </div>

    <!-- Log -->
    <div class="col relative-position">
      <TrafficLog :logs="trafficLogs" @clear="clearLogs" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import TrafficLog, { type TrafficParams } from 'src/components/debug/TrafficLog.vue';
import TrafficStats from 'src/components/debug/TrafficStats.vue';

// --- STATE ---
const isEnabled = ref(false);
const trafficLogs = ref<TrafficParams[]>([]);
const totalMessages = ref(0);
const lastMsgType = ref('');
const mps = ref(0);
let msgCountLastSec = 0;
let mpsInterval: NodeJS.Timeout | null = null;

// --- LIFECYCLE ---
onMounted(() => {
  window.addEventListener('ws-debug', handleWsDebug);

  mpsInterval = setInterval(() => {
    mps.value = msgCountLastSec;
    msgCountLastSec = 0;
  }, 1000);
});

onUnmounted(() => {
  window.removeEventListener('ws-debug', handleWsDebug);
  if (mpsInterval) clearInterval(mpsInterval);
});

// --- FUNCTIONS ---
function handleWsDebug(e: Event) {
  if (!isEnabled.value) return;

  const detail = (e as CustomEvent).detail;
  if (!detail) return;

  totalMessages.value++;
  msgCountLastSec++;
  lastMsgType.value = detail.type;

  // Keep last 1000 logs
  if (trafficLogs.value.length > 1000) trafficLogs.value.shift();

  trafficLogs.value.push({
    type: detail.type,
    payload: detail,
    timestamp: Date.now(),
  });
}

function clearLogs() {
  trafficLogs.value = [];
  totalMessages.value = 0;
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid var(--q-third);
}
</style>
