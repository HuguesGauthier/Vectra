<template>
  <div class="vectra-chat column full-height relative-position" :style="customCssVars">
    <!-- Messages Area -->
    <div
      ref="scrollContainerRef"
      class="messages-container col overflow-auto q-px-md q-pt-md"
      @scroll="handleScroll"
    >
      <div class="messages-list column q-gutter-y-md q-pb-xl">
        <!-- Welcome Message -->
        <transition appear name="fade-in-up">
          <div
            v-if="messages.length === 0 && introMessage"
            class="welcome-message row justify-center q-my-xl"
          >
            <div class="text-center q-pa-lg">
              <q-avatar
                size="80px"
                class="q-mb-lg shadow-5 gradient-avatar"
                :style="welcomeAvatarStyle"
              >
                <img v-if="assistantAvatarUrl" :src="assistantAvatarUrl" />
                <span v-else class="text-h4 text-white">{{ assistantInitials }}</span>
              </q-avatar>
              <div class="text-h4 text-weight-bold q-mb-sm text-white">
                {{ introMessage.title }}
              </div>
              <div class="text-subtitle1 text-grey-4 q-px-xl" style="opacity: 0.8; line-height: 1.6;">
                {{ introMessage.subtitle }}
              </div>
            </div>
          </div>
        </transition>

        <!-- Message List -->
        <transition-group name="message-list">
          <VectraChatMessage
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
            :assistant="assistant"
            :assistant-avatar-url="assistantAvatarUrl"
          />
        </transition-group>

        <div
          v-if="
            (loading ?? false) && (!messages.length || messages.slice(-1)[0]?.sender === 'user')
          "
          class="typing-indicator-wrapper row q-mt-md"
        >
          <div class="typing-indicator glass-panel row items-center q-px-md q-py-sm">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
    </div>

    <div class="input-container-wrapper q-pa-md">
      <VectraChatInput
        ref="chatInputRef"
        :loading="loading ?? false"
        :disabled="disabled ?? false"
        @send="onSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { assistantService, type Assistant } from 'src/services/assistantService';
import { usePublicChatStore } from 'src/stores/publicChatStore';
import type { ChatMessage } from '../composables/useChatStream';

import VectraChatMessage from './VectraChatMessage.vue';
import VectraChatInput from './VectraChatInput.vue';

const props = defineProps<{
  assistantId: string;
  assistantColor?: string;
  assistant: Assistant | null;
  loading?: boolean;
  disabled?: boolean;
  messages: ChatMessage[];
}>();

const emit = defineEmits<{
  (e: 'message-sent', text: string): void;
}>();

const { t } = useI18n();
const store = usePublicChatStore();

// Refs
const scrollContainerRef = ref<HTMLElement | null>(null);
const chatInputRef = ref<InstanceType<typeof VectraChatInput> | null>(null);

// State
const isUserScrolling = ref(false);
const showScrollToBottom = ref(false);
const assistantAvatarBlob = ref<string | null>(null);

// --- Computed ---

const customCssVars = computed(() => {
  return {
    '--chat-font-size': `${store.fontSize}px`,
  };
});

// Calculate an elegant gradient for the welcome avatar based on setup color
const welcomeAvatarStyle = computed(() => {
  const baseColor = props.assistantColor || 'var(--q-primary)';
  // If it's a CSS variable or invalid hex, fallback to basic background
  if (!baseColor.startsWith('#')) {
    return { backgroundColor: baseColor };
  }

  const hex = baseColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16) || 0;
  const g = parseInt(hex.substring(2, 4), 16) || 0;
  const b = parseInt(hex.substring(4, 6), 16) || 0;

  // Creates a vibrant, pure gradient
  return {
    background: `linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 1) 0%, rgba(${Math.max(0, r - 40)}, ${Math.max(0, g - 40)}, ${Math.max(0, b - 40)}, 1) 100%)`,
    boxShadow: `0 8px 24px rgba(${r}, ${g}, ${b}, 0.3)`,
  };
});

const introMessage = computed(() => {
  if (!props.assistant) return null;
  return {
    title: t('welcomeMessage', { name: props.assistant.name || '' }),
    subtitle: props.assistant.description || t('howCanIHelp'),
  };
});

const assistantInitials = computed(() => {
  const name = props.assistant?.name || 'AI';
  return name.charAt(0).toUpperCase();
});

const assistantAvatarUrl = computed(() => {
  if (assistantAvatarBlob.value) return assistantAvatarBlob.value;
  // If we have an image field but no blob yet, we don't return anything to show initials
  return null;
});

// --- Avatar Loading ---

watch(
  [() => props.assistant?.id, () => props.assistant?.avatar_image],
  async ([newId, newImage]) => {
    if (assistantAvatarBlob.value) {
      URL.revokeObjectURL(assistantAvatarBlob.value);
      assistantAvatarBlob.value = null;
    }

    if (newId && newImage) {
      try {
        const blob = await assistantService.getAvatarBlob(newId);
        assistantAvatarBlob.value = URL.createObjectURL(blob);
      } catch (e) {
        console.error('Failed to load avatar blob', e);
      }
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (assistantAvatarBlob.value) {
    URL.revokeObjectURL(assistantAvatarBlob.value);
  }
});

// --- Scrolling Logic ---

const handleScroll = () => {
  if (!scrollContainerRef.value) return;

  const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.value;
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

  // If user scrolled up more than 100px, they are considered to be manually scrolling
  isUserScrolling.value = distanceFromBottom > 100;
  showScrollToBottom.value = false; // Always false now that FAB is removed
};

const scrollToBottom = async (force = false) => {
  await nextTick();
  if (!scrollContainerRef.value) return;

  // If generating (loading) or forced, and not scrolled up too far, auto-scroll to bottom
  if (force || !isUserScrolling.value || props.loading) {
    scrollContainerRef.value.scrollTo({
      top: scrollContainerRef.value.scrollHeight,
      behavior: 'auto',
    });
  }
};

// Watch for specific message changes that dictate scrolling
watch(
  () => props.messages,
  () => {
    void scrollToBottom();
  },
  { deep: true },
);

// If loading finishes, ensure we are at bottom
watch(
  () => props.loading,
  (newVal) => {
    if (!newVal) {
      void scrollToBottom();
    }
  },
);

// --- Methods ---

const onSend = (text: string) => {
  emit('message-sent', text);
  isUserScrolling.value = false; // Reset scroll lock on send
  setTimeout(() => {
    void scrollToBottom(true);
  }, 50);
};

// Exposed method for external components (like TrendingPanel)
const setInputText = (text: string) => {
  if (chatInputRef.value) {
    chatInputRef.value.setText(text);
  }
};

defineExpose({
  setInputText,
});
</script>

<style scoped>
.vectra-chat {
  background-color: var(--q-fifth);
  font-family: inherit;
  font-size: var(--chat-font-size, 15px);
}

.messages-container {
  scroll-behavior: smooth;
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.input-container-wrapper {
  background: linear-gradient(to top, var(--q-fifth) 60%, transparent);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

/* Glass panel utility */
.glass-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}

/* Typing indicator dots */
.typing-indicator {
  display: inline-flex;
  gap: 4px;
  border-radius: 20px;
}

.typing-indicator .dot {
  width: 6px;
  height: 6px;
  background-color: var(--q-primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}
.typing-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* Message List Transitions */
.message-list-enter-active,
.message-list-leave-active {
  transition: all 0.3s ease;
}
.message-list-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.message-list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.fade-in-up-enter-active {
  transition: all 0.5s ease;
}
.fade-in-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.gradient-avatar {
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease;
}
.gradient-avatar:hover {
  transform: scale(1.05);
}
</style>
