<template>
  <ChatLayout :right-drawer-open="showTrending">
    <template #header>
      <ChatHeader :assistant-id="assistantId" :assistant="currentAssistant" />
    </template>

    <template #trending-toggle>
      <div
        class="absolute row no-wrap items-center q-gutter-x-sm"
        style="top: 12px; left: 12px; z-index: 101"
      >
        <q-btn flat round dense icon="add_comment" @click="onReset">
          <q-tooltip>{{ $t('newConversation') }}</q-tooltip>
        </q-btn>

        <!-- Font Size Selection -->
        <div
          class="row no-wrap items-center q-px-sm"
          style="
            height: 32px;
            background: var(--q-secondary);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
          "
        >
          <q-btn
            flat
            round
            dense
            icon="text_decrease"
            size="xs"
            @click.stop="store.decreaseFontSize"
            style="min-width: 24px"
          >
            <q-tooltip>Réduire la police</q-tooltip>
          </q-btn>

          <span
            class="text-caption q-px-xs text-weight-bold"
            style="min-width: 28px; text-align: center; font-size: 11px; opacity: 0.8"
          >
            {{ store.fontSize }}
          </span>

          <q-btn
            flat
            round
            dense
            icon="text_increase"
            size="xs"
            @click.stop="store.increaseFontSize"
            style="min-width: 24px"
          >
            <q-tooltip>Agrandir la police</q-tooltip>
          </q-btn>
        </div>

        <q-btn flat round dense icon="whatshot" @click="showTrending = !showTrending">
          <q-tooltip>Questions fréquentes</q-tooltip>
        </q-btn>
      </div>
    </template>
    <template #messages>
      <!-- Warning for non-vectorized assistant -->
      <div
        v-if="currentAssistant && currentAssistant.is_vectorized === false"
        class="q-px-md q-pt-md"
      >
        <q-banner dense rounded class="bg-warning text-black">
          <template #avatar>
            <q-icon name="warning" color="black" />
          </template>
          {{ $t('assistantNotVectorized') }}
          {{ $t('vectorizeSourcesToEnableChat') }}
        </q-banner>
      </div>

      <VectraChat
        ref="vectraChatRef"
        :assistant-id="assistantId"
        :assistant-color="currentAssistant?.avatar_bg_color || ''"
        :assistant="currentAssistant"
        :loading="loading"
        :disabled="currentAssistant?.is_vectorized === false"
        :messages="messages"
        @message-sent="onMessageSent"
      />
    </template>

    <template #trending-panel>
      <ChatTrendingPanel
        :is-open="showTrending"
        :assistant-id="assistantId"
        @select="onTrendingSelect"
        @trending-open="showTrending = true"
        @trending-close="showTrending = false"
      />
    </template>
  </ChatLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { useChatStream } from '../composables/useChatStream';
import { assistantService } from 'src/services/assistantService';
import type { Assistant } from 'src/services/assistantService';
import { useAuthStore } from 'src/stores/authStore';
import { usePublicChatStore } from 'src/stores/publicChatStore';
import { useNotification } from 'src/composables/useNotification';
import { api } from 'boot/axios';
import ChatHeader from '../components/ChatHeader.vue';
import ChatLayout from '../components/ChatLayout.vue';
import VectraChat from '../components/VectraChat.vue';
import ChatTrendingPanel from '../components/ChatTrendingPanel.vue';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const { t } = useI18n();
// ... inside script ...

// Combine Text + HTML

const authStore = useAuthStore();
const store = usePublicChatStore();
const { notifySuccess } = useNotification();

const assistantId = computed(() => route.params.assistant_id as string);

const vectraChatRef = ref<InstanceType<typeof VectraChat> | null>(null);

const { messages, loading, sendMessage, initializeSession, reset } = useChatStream();

const currentAssistant = ref<Assistant | null>(null);
const showTrending = ref(false);

// Track if history is currently loading to prevent auto-scrolling issues
const isHistoryLoading = ref(false);

// --- Initialization ---

onMounted(async () => {
  window.addEventListener('vectra-open-file', handleOpenFile as EventListener);

  if (!assistantId.value) return;

  try {
    currentAssistant.value = await assistantService.getById(assistantId.value);

    // Auth Check
    if (currentAssistant.value?.user_authentication && !authStore.isAuthenticated) {
      await router.push({ name: 'Login', query: { redirect: route.fullPath } });
      return;
    }

    // Initialize Session
    isHistoryLoading.value = true;
    await initializeSession(assistantId.value);

    // UI will automatically be populated by the reactive `messages` array from useChatStream!
  } catch (err) {
    console.error('Initialization error:', err);
  } finally {
    isHistoryLoading.value = false;
  }
});

onUnmounted(() => {
  window.removeEventListener('vectra-open-file', handleOpenFile as EventListener);
});

const handleOpenFile = (event: CustomEvent) => {
  const docId = event.detail;
  if (docId) void openFile(docId as string);
};

const openFile = async (documentId: string) => {
  try {
    await api.post('/system/open-file', { document_id: documentId });
  } catch (err) {
    console.error('Failed to open file', err);
    $q.notify({ type: 'negative', message: 'Failed to open file' });
  }
};

const onMessageSent = async (text: string) => {
  console.log('[ChatPage] User sent message:', text);

  if (!assistantId.value) {
    console.error('[ChatPage] No assistant ID available for sending message');
    return;
  }

  // CRITICAL: Reset streaming state to ensure clean slate for new request
  showTrending.value = false;

  // Send the message via useChatStream composable
  await sendMessage(text, assistantId.value);
};

const onTrendingSelect = (text: string) => {
  showTrending.value = false;
  // Let trending modal close before sending
  setTimeout(() => {
    if (vectraChatRef.value) {
      vectraChatRef.value.setInputText(text);
    }
  }, 200);
};

const onReset = async () => {
  try {
    await reset();
    await router.replace({
      name: 'Chat',
      params: { assistant_id: assistantId.value },
      query: { t: Date.now() },
    });

    notifySuccess(t('conversationCleared'));
  } catch (e) {
    console.error(e);
  }
};
</script>

<style scoped>
/* Scoped styles if needed */
</style>
