<template>
  <q-card bordered flat class="bg-transparent q-mb-sm pulse-card">
    <q-card-section class="row items-center no-wrap q-py-sm">
      <q-btn
        round
        flat
        :icon="isPlaying ? 'pause' : 'play_arrow'"
        color="accent"
        :loading="isLoading"
        @click="togglePlay"
      />

      <div class="q-ml-sm column ellipsis" style="flex: 1">
        <div class="text-caption ellipsis" :style="{ color: textColor }">{{ fileName }}</div>
        <div class="text-xs text-weight-bold" :style="{ color: textColor }">
          Start: {{ formattedTime }}
        </div>
      </div>

      <!-- Pulse Animation (Visual Only) -->
      <div v-if="isPlaying" class="pulse-indicator q-ml-md">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </q-card-section>

    <!-- Hidden audio element -->
    <audio
      ref="audioRef"
      :src="audioUrl"
      @timeupdate="onTimeUpdate"
      @ended="onEnded"
      @loadedmetadata="onLoadedMetadata"
      @error="onError"
      preload="metadata"
    ></audio>
  </q-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { api } from 'boot/axios';

defineOptions({
  name: 'AudioSourceCard',
});

const props = withDefaults(
  defineProps<{
    fileId: string;
    sourcePath: string; // Keep for fallback display name
    timestamp: string; // "MM:SS" or "HH:MM:SS"
    startSeconds?: number;
    textColor?: string;
  }>(),
  {
    textColor: '#9e9e9e',
  },
);

const audioRef = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const isLoading = ref(false);

const fileName = computed(() => {
  if (!props.sourcePath) return 'Unknown Audio';
  let name = props.sourcePath.split(/[\\/]/).pop() || props.sourcePath;
  // Remove page number suffix like " (p. 1)" for audio files
  name = name.replace(/\s+\(p\.\s*\d+\)\s*$/, '');
  return name;
});

const formattedTime = computed(() => props.timestamp || '00:00');

// Construct streaming URL
const audioUrl = computed(() => {
  if (!props.fileId) return '';
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api/v1';
  return `${baseUrl.replace(/\/$/, '')}/audio/stream/${props.fileId}`;
});

const parseSeconds = (timestamp: string): number => {
  if (props.startSeconds !== undefined && props.startSeconds > 0) return props.startSeconds;

  const parts = timestamp.split(':').map(Number);
  if (parts.length === 2 && typeof parts[0] === 'number' && typeof parts[1] === 'number') {
    return parts[0] * 60 + parts[1];
  }
  if (
    parts.length === 3 &&
    typeof parts[0] === 'number' &&
    typeof parts[1] === 'number' &&
    typeof parts[2] === 'number'
  ) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  return 0;
};

const startTime = computed(() => parseSeconds(props.timestamp));

function togglePlay() {
  if (!audioRef.value) return;

  if (isPlaying.value) {
    audioRef.value.pause();
    isPlaying.value = false;
  } else {
    // Debug logging
    console.log('🎵 AudioSourceCard - Attempting to play:', {
      audioUrl: audioUrl.value,
      startTime: startTime.value,
      currentTime: audioRef.value.currentTime,
      volume: audioRef.value.volume,
      muted: audioRef.value.muted,
      duration: audioRef.value.duration,
    });

    // Ensure volume is set and not muted
    audioRef.value.volume = 1.0;
    audioRef.value.muted = false;

    // Check if current time is far from target (e.g. user seeked away)
    // For this simple card, "Play" means "Play this citation".
    if (Math.abs(audioRef.value.currentTime - startTime.value) > 2) {
      audioRef.value.currentTime = startTime.value;
    }

    audioRef.value.play().catch((error) => {
      console.error('❌ AudioSourceCard - Play error:', error);
    });
    isPlaying.value = true;
  }
}

function onEnded() {
  isPlaying.value = false;
}

function onTimeUpdate() {
  // Optional: Update progress bar if we had one
}

function onLoadedMetadata() {
  console.log('🎵 AudioSourceCard - Metadata loaded:', {
    duration: audioRef.value?.duration,
    startTime: startTime.value,
  });
}

function onError(event: Event) {
  const audio = event.target as HTMLAudioElement;
  console.error('❌ AudioSourceCard - Audio loading error:', {
    error: audio.error,
    errorCode: audio.error?.code,
    errorMessage: audio.error?.message,
    audioUrl: audioUrl.value,
  });
  isPlaying.value = false;
}

// Ensure we jump to time on first load if metadata loaded?
// No, we maximize privacy/silence. User must click play.
</script>

<style scoped>
.text-xs {
  font-size: 0.75rem;
  line-height: 1rem;
}

/* Pulse Animation */
.pulse-indicator {
  display: flex;
  align-items: center;
  height: 20px;
  gap: 3px;
}

.pulse-indicator span {
  display: block;
  width: 3px;
  height: 100%;
  background-color: var(--q-accent);
  border-radius: 2px;
  animation: pulse 1s infinite ease-in-out;
}

.pulse-indicator span:nth-child(2) {
  animation-delay: 0.2s;
  height: 70%;
}
.pulse-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes pulse {
  0%,
  100% {
    transform: scaleY(0.5);
    opacity: 0.5;
  }
  50% {
    transform: scaleY(1);
    opacity: 1;
  }
}

.pulse-card {
  transition: all 0.3s ease;
}
</style>
