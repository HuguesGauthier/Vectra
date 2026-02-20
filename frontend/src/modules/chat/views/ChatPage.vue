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

      <DeepChatWrapper
        ref="deepChatWrapperRef"
        :assistant-id="assistantId"
        :assistant-color="currentAssistant?.avatar_bg_color || ''"
        :assistant="currentAssistant"
        :loading="loading"
        :disabled="currentAssistant?.is_vectorized === false"
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';
import MarkdownIt from 'markdown-it';

// Services & Stores
import { assistantService, type Assistant } from 'src/services/assistantService';
import { useAuthStore } from 'src/stores/authStore';
import { usePublicChatStore } from 'src/stores/publicChatStore';

// Composables & Components
import { useChatStream, type ChatMessage } from '../composables/useChatStream';
import { useNotification } from 'src/composables/useNotification';
import ChatHeader from '../components/ChatHeader.vue';
import ChatLayout from '../components/ChatLayout.vue';
import DeepChatWrapper from '../components/DeepChatWrapper.vue';
import ChatTrendingPanel from '../components/ChatTrendingPanel.vue';
import { MessageRenderer } from '../services/MessageRenderer';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const { t } = useI18n();
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
});

// ... inside script ...

// ... (prepareMessagePayload) ...

// Combine Text + HTML

const authStore = useAuthStore();
const store = usePublicChatStore();
const { notifySuccess } = useNotification();

const assistantId = computed(() => route.params.assistant_id as string);

const deepChatWrapperRef = ref<InstanceType<typeof DeepChatWrapper> | null>(null);

const { messages, loading, sendMessage, initializeSession, reset } = useChatStream();

const currentAssistant = ref<Assistant | null>(null);

const showTrending = ref(false);

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

    // Initialize Session (track history loading)
    isHistoryLoading.value = true;
    await initializeSession(assistantId.value);

    // Note: initializeSession usually calls loadHistory internally if session exists.
    // We avoid calling loadHistory() explicitly again to prevent double-loading issues.

    // 1. Map all messages to Deep Chat format for batch loading
    // This is much more robust than individual addMessage calls which can race with watchers
    if (messages.value.length > 0) {
      console.log('[ChatPage] Batch loading history:', messages.value.length);
      const historyPayloads = messages.value
        .filter((msg) => {
          // Skip empty placeholder messages
          if (
            msg.sender === 'bot' &&
            !msg.text &&
            (!msg.contentBlocks || msg.contentBlocks.length === 0) &&
            !msg.visualization
          ) {
            return false;
          }
          return true;
        })
        .map((msg) => prepareMessagePayload(msg));

      if (deepChatWrapperRef.value) {
        (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).setHistory(historyPayloads);

        // Update stream offset to the end of history to prevent re-streaming
        const last = messages.value[messages.value.length - 1];
        if (last?.sender === 'bot') {
          currentStreamOffset.value = last.text?.length || 0;
        }
      }
    }

    // Wait for reactivity to process history
    await nextTick();
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

// --- Bridge Logic: Sync Vue State -> Deep Chat ---

const currentStreamOffset = ref(0);
const isHistoryLoading = ref(false);
const isBridgeStreamOpen = ref(false);
const isActivelyStreaming = ref(false); // Track ONLY new streaming responses, not history

// Reset all streaming state to initial values
const resetStreamingState = () => {
  console.log('[ChatPage] Resetting streaming state');
  isBridgeStreamOpen.value = false;
  isActivelyStreaming.value = false;
  currentStreamOffset.value = 0;
};

// Watch for assistant changes to prevent state leakage
// ... existing watchers ...
watch(
  assistantId,
  (newId, oldId) => {
    if (newId !== oldId) {
      console.log('[ChatPage] Assistant changed, resetting state');
      resetStreamingState();
      // Additional cleanup if needed
      messages.value = [];
    }
  },
  { immediate: true },
);

watch(
  () => messages.value.length,
  (newLen, oldLen) => {
    // CRITICAL: Skip processing new messages if we are loading history
    // We handle history via batch loading in onMounted
    if (isHistoryLoading.value) return;

    if (newLen > oldLen) {
      // New message added: reset stream offset
      currentStreamOffset.value = 0;

      const newMessages = messages.value.slice(oldLen);
      newMessages.forEach((msg) => {
        processAndAddMessage(msg);
      });
    }
  },
);

// Computed for precise tracking of the last bot message text
const lastBotMessageText = computed(() => {
  const last = messages.value[messages.value.length - 1];
  return last?.sender === 'bot' ? last.text : '';
});

// Computed for tracking pipeline steps of the last bot message
const lastBotSteps = computed(() => {
  const last = messages.value[messages.value.length - 1];
  return last?.sender === 'bot' ? last.steps : undefined;
});

// Watch text changes directly - This guarantees reactivity even if array watcher fails
watch(lastBotMessageText, (newText) => {
  // CRITICAL: Only bridge to DeepChat if we are actively streaming a NEW request
  // AND the bridge is open. History text updates should NOT trigger streamResponse.
  if (!isActivelyStreaming.value || !isBridgeStreamOpen.value || !newText) return;

  if (!deepChatWrapperRef.value) return;

  const offset = currentStreamOffset.value;
  if (newText.length > offset) {
    const chunk = newText.slice(offset);

    currentStreamOffset.value = newText.length;

    (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).streamResponse?.({
      text: chunk,
    });
  }
});

// Watch pipeline steps changes to update the injected header inside DeepChat
watch(
  lastBotSteps,
  (newSteps) => {
    if (!isActivelyStreaming.value || !isBridgeStreamOpen.value || !newSteps) return;

    if (deepChatWrapperRef.value) {
      (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).updatePipelineHeader?.(
        newSteps,
      );
    }
  },
  { deep: true },
);

// Define interface for the exposed methods of DeepChatWrapper
interface DeepChatWrapperExposed {
  addMessage: (msg: unknown) => void;
  streamResponse?: (payload: { text?: string; html?: string }, isFinal?: boolean) => void;
  appendToLastMessage?: (html: string) => void;
  updatePipelineHeader?: (steps: unknown[]) => void;
  registerChart: (id: string, config: unknown) => void;
  hydrateChartNow: (id: string, config: unknown) => void;
  clearHistory: () => void;
  setHistory: (history: unknown[]) => void;
  setInputText: (text: string) => void;
  getNativeElement?: () => { history?: unknown[] } | null;
}

watch(
  () => store.fontSize,
  () => {
    // Wait for Deep Chat to react to font size change (which triggers internal re-render)
    // We use a small delay to ensure the web component has processed the style change before we repopulate history
    setTimeout(() => {
      if (deepChatWrapperRef.value) {
        console.log('[ChatPage] Font size changed, restoring history...');

        if (messages.value.length === 0) {
          (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).clearHistory();
          return;
        }

        // 1. Map all messages to Deep Chat format
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const historyPayloads: any[] = [];
        messages.value.forEach((msg) => {
          // Skip empty placeholder messages
          if (
            msg.sender === 'bot' &&
            !msg.text &&
            (!msg.contentBlocks || msg.contentBlocks.length === 0) &&
            !msg.visualization
          ) {
            return;
          }
          const payload = prepareMessagePayload(msg);
          historyPayloads.push(payload);
        });

        // 2. Atomically set history
        console.log(`[ChatPage] Setting history with ${historyPayloads.length} items`);
        (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).setHistory(historyPayloads);
      }
    }, 100);
  },
);

watch(
  () => loading.value,
  async (newVal) => {
    console.log(
      '[ChatPage] Loading changed:',
      newVal,
      'isBridgeStreamOpen:',
      isBridgeStreamOpen.value,
    );

    if (newVal) {
      // START: Generation started
      // Force active streaming state ON
      isActivelyStreaming.value = true;
      if (!isBridgeStreamOpen.value) {
        console.log('[ChatPage] Starting stream bridge');
        isBridgeStreamOpen.value = true;
        currentStreamOffset.value = 0;
      }
    } else if (!newVal && deepChatWrapperRef.value && isBridgeStreamOpen.value) {
      // END: No more streaming and we were bridging
      console.log('[ChatPage] Ending stream bridge - finalizing message');
      await nextTick();

      const lastBotMsg = messages.value[messages.value.length - 1];
      const text = lastBotMessageText.value;
      const offset = currentStreamOffset.value;

      // First, close the text stream properly
      const payload: { text?: string } = {};
      if (text.length > offset) {
        payload.text = text.slice(offset);
        currentStreamOffset.value = text.length;
      }

      // Always close the stream with text (or empty if fully streamed)
      console.log('[ChatPage] Closing text stream');
      (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).streamResponse?.(
        payload,
        true,
      );

      // Then, AFTER closing the stream, append additional HTML content
      const hasAdditionalContent =
        lastBotMsg &&
        lastBotMsg.sender === 'bot' &&
        ((lastBotMsg.steps && lastBotMsg.steps.length > 0) ||
          (lastBotMsg.sources && lastBotMsg.sources.length > 0) ||
          (lastBotMsg.contentBlocks && lastBotMsg.contentBlocks.length > 0) ||
          lastBotMsg.visualization);

      let chartId = null;

      if (hasAdditionalContent && lastBotMsg) {
        console.log('[ChatPage] Found additional content, appending to last message');

        // Build HTML for additional content
        let additionalHtml = '';

        // A. Content Blocks
        if (lastBotMsg.contentBlocks && lastBotMsg.contentBlocks.length > 0) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          lastBotMsg.contentBlocks.forEach((b: any) => {
            if (b.type === 'tech-sheet') {
              additionalHtml += MessageRenderer.renderTechSheet(b.data);
            } else if (b.type === 'table') {
              additionalHtml += MessageRenderer.renderTable(b.data);
            }
          });
        }

        // B. Visualization
        if (lastBotMsg.visualization) {
          const vizHtml = MessageRenderer.renderVisualizationContainer();
          additionalHtml += vizHtml;
          const match = vizHtml.match(/id="(chart-[^"]+)"/);
          if (match && match[1]) {
            chartId = match[1];
          }
        }

        // C. Steps
        if (lastBotMsg.steps && lastBotMsg.steps.length > 0) {
          console.log(
            '[ChatPage] Adding steps to additional HTML, count:',
            lastBotMsg.steps.length,
          );
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          additionalHtml += MessageRenderer.renderSteps(lastBotMsg.steps as any);
        }

        // D. Sources
        if (lastBotMsg.sources && lastBotMsg.sources.length > 0) {
          console.log(
            '[ChatPage] Adding sources to additional HTML, count:',
            lastBotMsg.sources.length,
          );
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          additionalHtml += MessageRenderer.renderSources(lastBotMsg.sources as any);
        }

        // Append the additional HTML to the last message
        if (additionalHtml) {
          console.log('[ChatPage] Appending HTML to last message, length:', additionalHtml.length);
          await nextTick(); // Wait for stream close to complete
          (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).appendToLastMessage?.(
            additionalHtml,
          );
        }
      }

      // Schedule Hydration if needed
      if (chartId && lastBotMsg?.visualization) {
        console.log('[ChatPage] Scheduling hydration for:', chartId);
        await nextTick(); // Wait for Vue
        await nextTick(); // Wait for DeepChat Render
        setTimeout(() => {
          if (deepChatWrapperRef.value) {
            (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).hydrateChartNow(
              chartId,
              lastBotMsg.visualization,
            );
          }
        }, 150);
      }

      // Explicitly reset state after successful completion
      resetStreamingState();
      console.log('[ChatPage] Stream bridge ended');
    }
  },
);

function processAndAddMessage(msg: ChatMessage) {
  if (!deepChatWrapperRef.value) return;

  // 1. History Loading vs Live Chat
  // If we are NOT loading history, and this is a USER message, we skip adding it.
  // Deep Chat (native) already displays the user's input immediately.
  // We only add user messages if we are loading history.
  if (msg.sender === 'user' && !isHistoryLoading.value) {
    return;
  }

  // 2. Native Streaming support:
  // If useChatStream adds an empty/placeholder bot message, we SKIP adding it manually using addMessage.
  // We rely on Deep Chat's 'activeSignals' (triggered by the user request) to show the loading bubble,
  // and then 'streamResponse' (above) to populate it via onResponse.
  if (msg.sender === 'bot' && (!msg.text || msg.text === '...')) {
    return;
  }

  const payload = prepareMessagePayload(msg);
  deepChatWrapperRef.value.addMessage(payload);
}

function prepareMessagePayload(msg: ChatMessage) {
  const role = msg.sender === 'user' ? 'user' : 'ai';
  let htmlContent = '';
  const textContent = msg.text || '';

  console.log('[ChatPage] prepareMessagePayload:', {
    sender: msg.sender,
    textLength: textContent.length,
    hasViz: !!msg.visualization,
    hasSteps: !!msg.steps?.length,
    hasSources: !!msg.sources?.length,
  });

  // 1. Tech Sheets & Tables
  if (msg.contentBlocks) {
    msg.contentBlocks.forEach((b) => {
      if (b.type === 'tech-sheet') {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        htmlContent += MessageRenderer.renderTechSheet(b.data as any);
      } else if (b.type === 'table') {
        console.log('[ChatPage] Rendering TABLE block:', b.data);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        htmlContent += MessageRenderer.renderTable(b.data as any);
      }
    });
  }

  // 2. Visualization
  if (msg.visualization) {
    const vizHtml = MessageRenderer.renderVisualizationContainer();
    htmlContent += vizHtml;

    const match = vizHtml.match(/id="(chart-[^"]+)"/);
    if (match && match[1] && deepChatWrapperRef.value) {
      deepChatWrapperRef.value.registerChart(match[1], msg.visualization);
    }
  }

  // 3. Steps
  if (msg.steps && msg.steps.length > 0) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    htmlContent += MessageRenderer.renderSteps(msg.steps as any);
  }

  // 4. Sources
  if (msg.sources && msg.sources.length > 0) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    htmlContent += MessageRenderer.renderSources(msg.sources as any);
  }

  // Combine Text + HTML
  if (htmlContent) {
    if (textContent) {
      // Render Markdown to HTML to ensure consistent display on reload
      // This mimics DeepChat's internal rendering but inside our wrapper
      const renderedText = md.render(textContent);
      htmlContent =
        `<div class="deep-chat-text-wrapper" style="margin-bottom: 8px;">${renderedText}</div>` +
        htmlContent;
    }
    console.log('[ChatPage] Returning HTML payload, text included:', !!textContent);
    console.log('[ChatPage] HTML Content (first 500 chars):', htmlContent.substring(0, 500));
    return { role, html: htmlContent };
  }

  // Fallback for empty messages? No, return empty structure or just text.
  // if (!textContent && role === 'ai') { return { role, text: '...' }; }

  console.log('[ChatPage] Returning text-only payload');
  return { role, text: textContent };
}

// --- Event Handlers ---

const onMessageSent = async (text: string) => {
  console.log('[ChatPage] User sent message:', text);

  if (!assistantId.value) {
    console.error('[ChatPage] No assistant ID available for sending message');
    return;
  }

  // CRITICAL: Reset streaming state to ensure clean slate for new request
  resetStreamingState();
  showTrending.value = false;

  // Set actively streaming flag
  isActivelyStreaming.value = true;

  // Send the message via useChatStream composable
  await sendMessage(text, assistantId.value);
};

const onTrendingSelect = (text: string) => {
  showTrending.value = false;
  // Wait for binding to settle and drawer to close
  setTimeout(() => {
    if (deepChatWrapperRef.value) {
      (deepChatWrapperRef.value as unknown as DeepChatWrapperExposed).setInputText(text);
    }
  }, 200);
};

const onReset = async () => {
  try {
    if (deepChatWrapperRef.value) {
      deepChatWrapperRef.value.clearHistory();
    }
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
