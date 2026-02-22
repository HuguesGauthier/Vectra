<template>
  <div class="vectra-chat-input-wrapper relative-position" :class="{ 'disabled-state': disabled }">
    <!-- Active STT Pulse -->
    <div v-if="isListening" class="stt-active-bg absolute-full rounded-borders"></div>

    <div class="input-glass row items-center q-px-sm q-py-xs">
      <!-- Speech to text button -->
      <q-btn
        flat
        round
        dense
        :color="isListening ? 'negative' : 'grey-5'"
        :icon="isListening ? 'mic' : 'mic_none'"
        class="stt-button"
        :class="{ 'pulsing-mic': isListening }"
        @click="toggleListening"
        :disable="disabled || !isSpeechRecognitionSupported"
      >
        <q-tooltip>{{ isListening ? $t('stopListening') : $t('startListening') }}</q-tooltip>
      </q-btn>

      <!-- Input Field -->
      <q-input
        ref="inputRef"
        v-model="inputText"
        type="textarea"
        autogrow
        borderless
        dense
        :disable="disabled || loading"
        :placeholder="disabled ? $t('chatDisabledPlaceholder') : $t('typeMessage')"
        class="col q-mx-sm chat-input-field"
        @keydown.enter.prevent="handleEnter"
        input-style="max-height: 200px; min-height: 40px; padding: 10px 0 6px 0;"
      />

      <!-- Send button -->
      <q-btn
        flat
        round
        dense
        :color="canSend ? 'white' : 'grey-7'"
        icon="send"
        class="send-button"
        :class="{ 'opacity-50': !canSend }"
        :disable="loading || disabled"
        :loading="loading"
        @click="send"
      >
        <template v-slot:loading>
          <q-spinner-dots size="1.5em" />
        </template>
        <q-tooltip>{{ $t('send') }}</q-tooltip>
      </q-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';

const props = defineProps<{
  loading?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'send', text: string): void;
}>();

// Refs
const inputText = ref('');
const inputRef = ref<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
const isListening = ref(false);

// STT
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let recognition: any = null;
const isSpeechRecognitionSupported =
  'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;

if (isSpeechRecognitionSupported) {
  const SpeechRecognition =
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;

  // Try to use app language
  const appLocale = localStorage.getItem('app_language') || 'en-US';
  recognition.lang = appLocale === 'fr' ? 'fr-FR' : appLocale;

  recognition.onstart = () => {
    isListening.value = true;
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  recognition.onresult = (event: any) => {
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      }
    }

    if (finalTranscript) {
      inputText.value += (inputText.value ? ' ' : '') + finalTranscript;
    }

    // Optional: could show interim in a specific span or placeholder
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  recognition.onerror = (event: any) => {
    console.error('Speech recognition error', event.error);
    isListening.value = false;
  };

  recognition.onend = () => {
    isListening.value = false;
  };
}

const toggleListening = () => {
  if (!recognition) return;

  if (isListening.value) {
    recognition.stop();
  } else {
    try {
      recognition.start();
    } catch (e) {
      // Catch DOMException if already started
      console.warn('Speech recognition already started', e);
    }
  }
};

onUnmounted(() => {
  if (recognition && isListening.value) {
    recognition.stop();
  }
});

// Computed
const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !props.loading && !props.disabled;
});

// Methods
const handleEnter = (e: KeyboardEvent) => {
  if (e.shiftKey) {
    // Let it act normally (new line)
    return;
  }

  // Submit on enter
  if (canSend.value) {
    send();
  }
};

const send = () => {
  if (!canSend.value || props.loading || props.disabled) return;

  const textToSend = inputText.value.trim();
  emit('send', textToSend);

  // Clear input
  inputText.value = '';

  // Refocus input
  setTimeout(() => {
    if (inputRef.value) {
      inputRef.value.focus();
    }
  }, 100);
};

// Exposed method for external templates (like TrendingPane)
const setText = (text: string) => {
  inputText.value = text;
  send();
};

defineExpose({
  setText,
});
</script>

<style scoped>
.input-glass {
  background: var(--q-secondary);
  border-radius: 32px;
  border: 1px solid var(--q-third);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  position: relative;
  z-index: 2;
  box-shadow: none;
}

.input-glass:focus-within {
  border-color: var(--q-sixth);
  background: var(--q-secondary);
  box-shadow: none;
  transform: translateY(-2px);
}

.chat-input-field {
  color: var(--q-text-main);
  font-size: 16px;
  padding: 4px 0;
}

/* Scrollbar for the textarea when max-height is reached */
::v-deep(.chat-input-field textarea::-webkit-scrollbar) {
  width: 6px;
}
::v-deep(.chat-input-field textarea::-webkit-scrollbar-thumb) {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.send-button {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.send-button:not(.opacity-50):hover {
  transform: scale(1.15) rotate(-10deg);
  color: var(--q-sixth) !important;
}

.stt-button {
  transition: all 0.3s ease;
}

.stt-button:hover {
  transform: scale(1.1);
}

.opacity-50 {
  opacity: 0.3;
  cursor: not-allowed;
}

.disabled-state {
  opacity: 0.6;
  pointer-events: none;
}

/* Pulsing Mic */
.stt-active-bg {
  background: radial-gradient(circle, rgba(244, 67, 54, 0.15) 0%, transparent 70%);
  z-index: 1;
  animation: pulse-bg 2s infinite ease-in-out;
  pointer-events: none;
  transform: scale(1.2);
}

.pulsing-mic {
  animation: pulse-icon 2s infinite ease-in-out;
}

@keyframes pulse-icon {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
    text-shadow: 0 0 10px rgba(244, 67, 54, 0.8);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes pulse-bg {
  0% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
  100% {
    opacity: 0.5;
    transform: scale(1);
  }
}
</style>
