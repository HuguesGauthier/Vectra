import { ref, onUnmounted } from 'vue';
import { api } from 'boot/axios';
import { useI18n } from 'vue-i18n';
import { uid } from 'quasar';
import { useRouter, useRoute } from 'vue-router';
import type { Source } from 'src/stores/publicChatStore';

// --- Types ---

export interface ChatStep {
  step_type: string;
  status: 'running' | 'completed' | 'failed' | 'error';
  label: string;
  duration?: number;
  tokens?: { input: number; output: number };
  sourceCount?: number;
  isSubStep?: boolean;
  metadata?: Record<string, unknown>;
}

export interface ContentBlock {
  type: 'text' | 'tech-sheet' | 'table';
  data: unknown; // Use precise types if available
}

export interface ChatMessage {
  id: string; // Changed to string for uid()
  text: string;
  contentBlocks: ContentBlock[];
  sender: 'user' | 'bot';
  sources?: Source[];
  steps?: ChatStep[];
  statusMessage?: string;
  visualization?: unknown;
}

// Discriminated Union for safer type handling
type StreamEvent =
  | { type: 'status'; message: string }
  | { type: 'token'; content: string }
  | { type: 'sources'; data: BackendSource[] }
  | { type: 'error'; message: string }
  | {
      type: 'step';
      step_type: string;
      status: ChatStep['status'];
      label?: string;
      duration?: number;
      payload?: Record<string, unknown>;
    }
  | { type: 'visualization'; data: unknown }
  | {
      type: 'content_block' | 'tech-sheet';
      block_type?: ContentBlock['type'];
      content?: unknown;
      data?: unknown;
    };

interface BackendSource {
  id: string;
  text: string;
  metadata: Record<string, unknown>;
  score?: number;
}

// --- Composable ---

export function useChatStream() {
  const { t, locale } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const messages = ref<ChatMessage[]>([]);
  const loading = ref(false);
  const error = ref('');
  const sessionId = ref('');
  const instanceId = uid();
  console.log('useChatStream init. InstanceID:', instanceId);

  let abortController: AbortController | null = null;

  // Cleanup on unmount
  onUnmounted(() => {
    if (abortController) abortController.abort();
  });

  async function initializeSession(assistantId: string) {
    if (!assistantId) return;
    const key = `chat_session_${assistantId}`;
    const storedSession = localStorage.getItem(key);

    if (storedSession) {
      sessionId.value = storedSession;
      await loadHistory();
    } else {
      sessionId.value = uid();
      localStorage.setItem(key, sessionId.value);
    }
  }

  async function loadHistory(): Promise<void> {
    if (!sessionId.value) return;
    try {
      // Use configured API only
      const response = await api.get(`/chat/${sessionId.value}/history`);

      if (response.data?.messages && Array.isArray(response.data.messages)) {
        // Transform messages to ensure visualization data is in contentBlocks
        messages.value = response.data.messages.map((msg: ChatMessage) => {
          // Initialize contentBlocks if not present
          if (!msg.contentBlocks) {
            msg.contentBlocks = [];
          }

          // If message has text but no text block, add it
          if (msg.text && !msg.contentBlocks.some((b) => b.type === 'text')) {
            msg.contentBlocks.push({ type: 'text', data: msg.text });
          }

          // Transform visualization into contentBlocks if present
          if (msg.visualization && typeof msg.visualization === 'object') {
            const viz = msg.visualization as { type?: string; items?: unknown[] };

            // Handle tech-sheet type visualizations
            if (viz.type === 'tech-sheet' && Array.isArray(viz.items)) {
              // Add each tech sheet as a content block
              viz.items.forEach((item) => {
                msg.contentBlocks.push({
                  type: 'tech-sheet',
                  data: item,
                });
              });
            }
          }

          // Regenerate step labels from step_type (labels are not saved in DB)
          if (msg.steps && msg.steps.length > 0) {
            msg.steps = msg.steps.map((step) => {
              // Generate label from step_type using i18n
              const label = t(`pipelineSteps.${step.step_type}`) || step.step_type;

              // Map is_substep from metadata to isSubStep
              // Check both metadata.is_substep and direct is_substep property
              const isSubStep =
                (step.metadata?.is_substep as boolean | undefined) ||
                ((step as unknown as Record<string, unknown>).is_substep as boolean | undefined) ||
                false;

              return {
                ...step,
                label,
                isSubStep,
              };
            });

            // Generate 'completed' summary step if not present (only for assistant messages)
            if (msg.sender === 'bot') {
              const hasCompletedStep = msg.steps.some((s) => s.step_type === 'completed');

              if (!hasCompletedStep && msg.steps.length > 0) {
                // Calculate totals from all steps
                const totalInput = msg.steps.reduce((acc, s) => acc + (s.tokens?.input || 0), 0);
                const totalOutput = msg.steps.reduce((acc, s) => acc + (s.tokens?.output || 0), 0);

                // CRITICAL FIX: Don't sum durations (steps overlap in parallel)
                // Instead, find the actual elapsed time from start to last completion
                // Use the end_time of the last completed step as total duration
                let totalDuration = 0;
                if (msg.steps.length > 0) {
                  // Find the step with the latest end time
                  const lastStep = msg.steps.reduce((latest, current) => {
                    const currentStart = (current.metadata?.start_time as number | undefined) ?? 0;
                    const latestStart = (latest.metadata?.start_time as number | undefined) ?? 0;
                    const currentEnd = currentStart + (current.duration || 0);
                    const latestEnd = latestStart + (latest.duration || 0);
                    return currentEnd > latestEnd ? current : latest;
                  });

                  // Calculate total elapsed time from first step start to last step end
                  const starts = msg.steps
                    .map((s) => (s.metadata?.start_time as number | undefined) ?? 0)
                    .filter((t) => t > 0);
                  const firstStepStart = starts.length > 0 ? Math.min(...starts) : 0;
                  const lastStepStart = (lastStep.metadata?.start_time as number | undefined) ?? 0;
                  const lastStepEnd = lastStepStart + (lastStep.duration || 0);

                  if (firstStepStart > 0 && lastStepEnd > 0) {
                    totalDuration = Math.round((lastStepEnd - firstStepStart) * 1000) / 1000;
                  } else {
                    // Fallback: use the longest single step duration if timestamps unavailable
                    totalDuration = Math.max(...msg.steps.map((s) => s.duration || 0));
                  }
                }

                // Add completed step at the beginning (create new array for reactivity)
                const completedStep: ChatStep = {
                  step_type: 'completed',
                  status: 'completed',
                  label: t('pipelineSteps.completed') || 'Completed',
                  duration: totalDuration,
                  tokens: { input: totalInput, output: totalOutput },
                };

                msg.steps = [completedStep, ...msg.steps];
              }
            }
          }

          return msg;
        });
      }
    } catch (err) {
      console.warn('Failed to load chat history:', err);
    }
  }

  // Extracted stream processor
  async function processStream(body: ReadableStream<Uint8Array>, targetMsgId: string) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const event = JSON.parse(line) as StreamEvent;
          handleStreamEvent(event, targetMsgId);
        } catch (e) {
          console.error('Error parsing stream line:', e, 'Line content:', line);
        }
      }
    }

    // Process remaining buffer if any
    if (buffer.trim()) {
      try {
        const event = JSON.parse(buffer) as StreamEvent;
        handleStreamEvent(event, targetMsgId);
      } catch (e) {
        console.error('Error parsing final stream line:', e);
      }
    }
  }

  function handleStreamEvent(event: StreamEvent, msgId: string): boolean {
    const botMsg = messages.value.find((m) => m.id === msgId);
    if (!botMsg) return false;

    if (!botMsg.contentBlocks) botMsg.contentBlocks = [];

    switch (event.type) {
      case 'status':
        botMsg.statusMessage = event.message;
        break;

      case 'token': {
        botMsg.statusMessage = '';
        const text = event.content || '';
        botMsg.text += text;

        // Update or create text block

        // Update or create text block
        const lastBlock = botMsg.contentBlocks[botMsg.contentBlocks.length - 1];
        if (lastBlock?.type === 'text') {
          // Cast to string safely or stringify if needed, but token content is string
          lastBlock.data = (lastBlock.data as string) + text;
        } else {
          botMsg.contentBlocks.push({ type: 'text', data: text });
        }
        break;
      }

      case 'content_block':
      case 'tech-sheet':
        botMsg.contentBlocks.push({
          type: event.block_type || 'tech-sheet',
          // Prioritize 'content', fallback to 'data'
          data: event.content || event.data,
        });
        break;

      case 'step':
        return handleStepEvent(botMsg, event);

      case 'sources':
        botMsg.sources = processSources(event.data || []);
        break;

      case 'visualization':
        botMsg.visualization = event.data;
        break;

      case 'error':
        // Use a clearer error representation
        botMsg.text += `\n\n⚠️ Error: ${event.message}`;
        error.value = event.message;
        break;
    }

    return false;
  }

  function handleStepEvent(
    botMsg: ChatMessage,
    event: Extract<StreamEvent, { type: 'step' }>,
  ): boolean {
    // Nested Step Update Logic
    if (!botMsg.steps) botMsg.steps = [];

    // Dynamic Label Logic
    let label = event.label || t(`pipelineSteps.${event.step_type}`);
    // Cache specific logic
    if (event.step_type === 'cache_lookup' && event.status === 'completed' && event.payload) {
      label = event.payload.hit ? t('pipelineSteps.cache_hit') : t('pipelineSteps.cache_miss');
    }

    const payload = event.payload as
      | { tokens?: { input: number; output: number }; is_substep?: boolean; source_count?: number }
      | undefined;

    const newStep: ChatStep = {
      step_type: event.step_type,
      status: event.status,
      label,
      ...(event.duration !== undefined ? { duration: event.duration } : {}),
      ...(payload?.tokens ? { tokens: payload.tokens } : {}),
      ...(payload?.is_substep !== undefined ? { isSubStep: payload.is_substep } : {}),
      ...(payload?.source_count !== undefined ? { sourceCount: payload.source_count } : {}),
      ...(payload?.source_count !== undefined ? { sourceCount: payload.source_count } : {}),
    };

    // Calculate totals for 'completed' step if missing
    if (newStep.step_type === 'completed' && newStep.status === 'completed') {
      if (!newStep.tokens) {
        const totalInput = botMsg.steps.reduce((acc, s) => acc + (s.tokens?.input || 0), 0);
        const totalOutput = botMsg.steps.reduce((acc, s) => acc + (s.tokens?.output || 0), 0);
        if (totalInput > 0 || totalOutput > 0) {
          newStep.tokens = { input: totalInput, output: totalOutput };
        }
      }
      // Note: Duration is usually provided by the backend for the overall request.
      // If missing, we could sum it up, but backend duration is more accurate (wall clock).
    }

    // Update existing running step or push new
    let foundIndex = -1;
    // Search nested: find the LAST running step of the same type
    for (let i = botMsg.steps.length - 1; i >= 0; i--) {
      const s = botMsg.steps[i];
      if (s && s.step_type === newStep.step_type) {
        // Option A: Step is currently running
        if (s.status === 'running') {
          foundIndex = i;
          break;
        }
        // Option B: Sub-step update/refinement (even if completed)
        if (
          newStep.isSubStep &&
          s.isSubStep &&
          newStep.status === 'completed' &&
          s.status === 'completed'
        ) {
          foundIndex = i;
          break;
        }
      }
    }

    if (foundIndex !== -1) {
      // Merge logic: preserve existing data if new event is a partial update (e.g. metadata/count refinement)
      const oldStep = botMsg.steps[foundIndex];
      if (oldStep) {
        if (newStep.duration === undefined && oldStep.duration !== undefined) {
          newStep.duration = oldStep.duration;
        }
        if (newStep.tokens === undefined && oldStep.tokens !== undefined) {
          newStep.tokens = oldStep.tokens;
        }
        if (newStep.sourceCount === undefined && oldStep.sourceCount !== undefined) {
          newStep.sourceCount = oldStep.sourceCount;
        }
        // FIX: Preserve isSubStep if not present in new event (often missing in completion events)
        if (newStep.isSubStep === undefined && oldStep.isSubStep !== undefined) {
          newStep.isSubStep = oldStep.isSubStep;
        }
      }

      botMsg.steps[foundIndex] = newStep;
    } else {
      botMsg.steps.push(newStep);
    }
    return newStep.step_type === 'completed' && newStep.status === 'completed';
  }

  function processSources(backendSources: BackendSource[]): Source[] {
    return backendSources.map((s) => {
      const metadata = s.metadata || {};
      const fileName = (metadata.file_name ||
        metadata.filename ||
        metadata.name ||
        t('unknownDocument')) as string;
      const rawPageLabel = metadata.page_label || metadata.page_number || metadata.page;
      const pageLabel =
        typeof rawPageLabel === 'string' || typeof rawPageLabel === 'number'
          ? String(rawPageLabel)
          : undefined;
      const displayName = pageLabel ? `${fileName} (p. ${pageLabel})` : fileName;

      let type: 'pdf' | 'docx' | 'txt' | 'web' | 'audio' = 'txt';
      const lowerName = fileName.toLowerCase();

      if (lowerName.endsWith('.pdf')) type = 'pdf';
      else if (lowerName.endsWith('.docx')) type = 'docx';
      else if (metadata.url) type = 'web';
      else if (
        ['.mp3', '.wav', '.m4a', '.flac', '.aac'].some((ext) => lowerName.endsWith(ext)) ||
        metadata.media_type === 'audio'
      ) {
        type = 'audio';
      }

      return {
        id: s.id,
        name: displayName,
        type,
        content: s.text,
        ...(metadata.url && typeof metadata.url === 'string' ? { url: metadata.url } : {}),
        ...(metadata.file_path && typeof metadata.file_path === 'string'
          ? { filePath: metadata.file_path }
          : {}),
        metadata,
      };
    });
  }

  async function sendMessage(text: string, assistantId: string) {
    if (!text.trim() || !assistantId) return;

    error.value = '';
    loading.value = true;

    // 1. Initialize session FIRST to prevent history overwrite race condition
    if (!sessionId.value) {
      await initializeSession(assistantId);
    }

    // 2. Push User Message
    messages.value.push({
      id: uid(),
      text: text,
      contentBlocks: [{ type: 'text', data: text }],
      sender: 'user',
    });

    // 3. Push Placeholder Bot Message
    const botMsgId = uid();
    const botMsg: ChatMessage = {
      id: botMsgId,
      text: '',
      contentBlocks: [],
      sender: 'bot',
      statusMessage: t('initializing'),
      steps: [],
    };
    messages.value.push(botMsg);

    try {
      if (abortController) abortController.abort();
      abortController = new AbortController();

      const baseURL = api.defaults.baseURL || '';
      // Fallback for fetch usage if needed, but we need the token.

      const response = await fetch(`${baseURL.replace(/\/$/, '')}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(localStorage.getItem('token')
            ? { Authorization: `Bearer ${localStorage.getItem('token')}` }
            : {}),
        },
        body: JSON.stringify({
          message: text,
          assistant_id: assistantId,
          session_id: sessionId.value,
          language: locale.value || 'en',
        }),
        signal: abortController.signal,
      });

      if (response.status === 401) {
        await router.push({ name: 'Login', query: { redirect: route.fullPath } });
        return;
      }

      if (!response.body) throw new Error('No response body');

      await processStream(response.body, botMsgId);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;

      // Update the specific message error state
      const msg = messages.value.find((m) => m.id === botMsgId);
      if (msg) msg.text += `\n\n❌ ${t('communicationError')}`;
      error.value = t('communicationError');
      console.error(err);
    } finally {
      loading.value = false;
      abortController = null;
    }
  }

  async function reset() {
    if (!sessionId.value) return;
    try {
      await api.delete(`/chat/${sessionId.value}`);
      console.log(`Backend session cleared: ${sessionId.value}`);
    } catch (e) {
      console.error('Failed to clear backend session:', e);
      throw e;
    }

    const key = `chat_session_${route.params.assistant_id as string}`;
    localStorage.removeItem(key);
    sessionId.value = uid();
    localStorage.setItem(key, sessionId.value);
    messages.value = [];
  }

  return {
    messages,
    loading,
    error,
    sessionId,
    sendMessage,
    initializeSession,
    loadHistory,
    reset,
    instanceId,
  };
}
