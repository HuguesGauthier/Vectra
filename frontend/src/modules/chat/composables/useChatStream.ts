import { ref, onUnmounted } from 'vue';
import { api } from 'boot/axios';
import { useI18n } from 'vue-i18n';
import { uid } from 'quasar';
import { useRouter, useRoute } from 'vue-router';
import type { Source } from 'src/stores/publicChatStore';

// --- Types ---

export interface ChatStep {
  step_id: string; // From backend span_id
  parent_id: string | undefined; // Explicit undefined for strict assignability
  step_type: string;
  status: 'running' | 'completed' | 'failed' | 'error';
  label: string;
  duration?: number | undefined;
  tokens?: { input: number; output: number } | undefined;
  sourceCount?: number | undefined;
  isSubStep?: boolean | undefined;
  sub_steps?: ChatStep[] | undefined;
  metadata?: Record<string, unknown> | undefined;
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
      step_id: string; // REQUIRED in V4
      parent_id?: string;
      label?: string; // Optional dynamic override
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

  // --- Direct callbacks for bypassing Vue reactivity batching ---
  // These fire synchronously per SSE event, unlike Vue watchers which batch.
  let _onTokenCallback: ((token: string) => void) | null = null;
  let _onStepCallback: ((step: ChatStep) => void) | null = null;

  const setOnToken = (cb: ((token: string) => void) | null) => {
    _onTokenCallback = cb;
  };
  const setOnStep = (cb: ((step: ChatStep) => void) | null) => {
    _onStepCallback = cb;
  };

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

          // Rebuild step labels and hierarchy from stored data.
          // The backend returns steps with sub_steps already nested (via get_summary).
          // We only need to regenerate i18n labels and isSubStep flags here.
          if (msg.steps && msg.steps.length > 0) {
            const enrichStep = (step: ChatStep, inherited_parent_id?: string): ChatStep => {
              // Prefer explicit parent_id, then inherited from recursive call
              const parent_id = step.parent_id || inherited_parent_id;
              const isSubStep = !!parent_id;

              // Let the backend override the default translated label if specified
              let label = step.label || t(`pipelineSteps.${step.step_type}`) || step.step_type;

              const modelName = step.metadata?.model_name as string | undefined;
              const modelProvider = step.metadata?.model_provider as string | undefined;

              if (modelName) {
                const providerMap: Record<string, string> = {
                  openai: 'OpenAI',
                  gemini: 'Google',
                  mistral: 'Mistral',
                  ollama: 'Ollama',
                  anthropic: 'Anthropic',
                  cohere: 'Cohere',
                };
                const displayProvider = modelProvider
                  ? providerMap[modelProvider.toLowerCase()] ||
                    modelProvider.charAt(0).toUpperCase() + modelProvider.slice(1)
                  : '';
                const displayModel = displayProvider
                  ? `${displayProvider} - ${modelName}`
                  : modelName;
                label = `${label} (${displayModel})`;
              }

              // Recursively enrich sub_steps
              const sub_steps = step.sub_steps?.map((ss) => enrichStep(ss, step.step_id));

              return { ...step, parent_id, label, isSubStep, sub_steps };
            };

            msg.steps = msg.steps.map((step) => enrichStep(step));

            // Generate 'completed' summary step if not present (only for bot messages)
            if (msg.sender === 'bot') {
              const hasCompletedStep = msg.steps.some((s) => s.step_type === 'completed');

              if (!hasCompletedStep && msg.steps.length > 0) {
                // Flatten all steps to compute totals
                const flattenAll = (steps: ChatStep[]): ChatStep[] =>
                  steps.flatMap((s) => [s, ...flattenAll(s.sub_steps || [])]);
                const allSteps = flattenAll(msg.steps);

                const totalInput = allSteps.reduce((acc, s) => acc + (s.tokens?.input || 0), 0);
                const totalOutput = allSteps.reduce((acc, s) => acc + (s.tokens?.output || 0), 0);
                const totalDuration = Math.max(...allSteps.map((s) => s.duration || 0));

                const completedStep: ChatStep = {
                  step_id: 'summary_completed',
                  parent_id: undefined,
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

        // Fire direct callback BEFORE Vue batches the update
        if (_onTokenCallback) _onTokenCallback(text);

        // Update or create text block
        const lastBlock = botMsg.contentBlocks[botMsg.contentBlocks.length - 1];
        if (lastBlock?.type === 'text') {
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

      case 'step': {
        const stepResult = handleStepEvent(botMsg, event);
        // Fire step callback with the resolved step
        if (_onStepCallback && botMsg.steps && botMsg.steps.length > 0) {
          const lastStep = botMsg.steps[botMsg.steps.length - 1];
          if (lastStep) _onStepCallback(lastStep);
        }
        return stepResult;
      }

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
    if (!botMsg.steps) botMsg.steps = [];

    // No step suppression: all steps are shown for full transparency.

    // 1. Resolve Label (Frontend-only translation)
    const baseLabel = t(`pipelineSteps.${event.step_type}`) || event.step_type;
    let label = event.label || baseLabel;

    // Cache specific logic
    if (event.step_type === 'cache_lookup' && event.status === 'completed' && event.payload) {
      label = event.payload.hit ? t('pipelineSteps.cache_hit') : t('pipelineSteps.cache_miss');
    }

    // Append model info if available in payload
    if (!event.label) {
      const modelName = event.payload?.model_name;
      const modelProvider = event.payload?.model_provider;

      if (typeof modelName === 'string' && modelName) {
        let displayModel = modelName;
        if (typeof modelProvider === 'string' && modelProvider) {
          const providerMap: Record<string, string> = {
            openai: 'OpenAI',
            gemini: 'Google',
            mistral: 'Mistral',
            ollama: 'Ollama',
            anthropic: 'Anthropic',
            cohere: 'Cohere',
          };
          const displayProvider = providerMap[modelProvider.toLowerCase()] || modelProvider;
          displayModel = `${displayProvider} - ${modelName}`;
        }
        label = `${baseLabel} (${displayModel})`;
      }
    }

    const payload = event.payload;
    const isSubStep = !!event.parent_id || !!payload?.is_substep;

    const newStep: ChatStep = {
      step_id: event.step_id,
      parent_id: event.parent_id,
      step_type: event.step_type,
      status: event.status,
      label,
      duration: event.duration,
      tokens: payload?.tokens as { input: number; output: number } | undefined,
      isSubStep: isSubStep,
      sourceCount: payload?.source_count as number | undefined,
      metadata: payload,
    };

    // 2. Nesting Logic (Recursive)
    if (event.parent_id) {
      const findParentRecursive = (steps: ChatStep[]): ChatStep | undefined => {
        for (const s of steps) {
          if (s.step_id === event.parent_id) return s;
          if (s.sub_steps) {
            const found = findParentRecursive(s.sub_steps);
            if (found) return found;
          }
        }
        return undefined;
      };

      const parent = findParentRecursive(botMsg.steps);
      if (parent) {
        if (!parent.sub_steps) parent.sub_steps = [];
        updateOrPushStep(parent.sub_steps, newStep);
        return false;
      }
    }

    // 3. Top-level sync
    if (botMsg.steps) {
      updateOrPushStep(botMsg.steps, newStep);
    }

    // 4. Update status message if applicable
    if (newStep.status === 'running' || (newStep.status === 'completed' && !botMsg.text)) {
      botMsg.statusMessage = newStep.label;
    }

    return newStep.step_type === 'completed' && newStep.status === 'completed';
  }

  function updateOrPushStep(steps: ChatStep[], newStep: ChatStep) {
    const idx = steps.findIndex((s) => s.step_id === newStep.step_id);
    const existingStep = steps[idx];
    if (existingStep) {
      // Preserve sub_steps if we are updating a parent
      if (existingStep.sub_steps && !newStep.sub_steps) {
        newStep.sub_steps = existingStep.sub_steps;
      }
      steps[idx] = newStep;
    } else {
      steps.push(newStep);
    }
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
    setOnToken,
    setOnStep,
  };
}
