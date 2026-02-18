<template>
  <div class="deep-chat-container">
    <deep-chat
      ref="deepChatRef"
      :demo="false"
      :style="customStyle"
      :messageStyles="messageStyles"
      :avatars="avatars"
      :textInput="textInput"
      :connect="connectConfig"
      :submitButtonStyles="submitButtonStyles"
      :introMessage="introMessage"
      :speechToText="speechToTextConfig"
    ></deep-chat>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, shallowRef, toRaw } from 'vue';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { assistantService, type Assistant } from 'src/services/assistantService';
import { usePublicChatStore } from 'src/stores/publicChatStore';
import { useAuthStore } from 'src/stores/authStore';
import { api } from 'boot/axios';

// Define props
const props = defineProps<{
  assistantId: string;
  assistantColor?: string;
  assistant: Assistant | null;
  loading?: boolean;
  disabled?: boolean;
}>();

const $q = useQuasar();
const { t, locale } = useI18n();

const emit = defineEmits<{
  (e: 'message-sent', message: string): void;
  (e: 'reset'): void;
}>();

const deepChatRef = ref<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
const store = usePublicChatStore();
const authStore = useAuthStore();

// --- Configuration ---

const customStyle = computed(() => ({
  width: '100%',
  height: '100%',
  backgroundColor: 'var(--q-fifth)',
  border: 'none',
  borderRadius: '0',
  '--text-input-container-background-color': 'var(--q-fourth)',
  '--text-input-background-color': 'var(--q-fourth)',
  '--text-input-border': 'none',
  '--messages-scroll-track-background-color': 'var(--q-primary)',
  '--messages-scroll-thumb-background-color': 'var(--q-primary)',
  '--messages-scroll-thumb-background-hover-color': 'var(--q-primary)',
}));

const messageStyles = computed(() => ({
  default: {
    shared: {
      bubble: {
        maxWidth: '85%',
        padding: '12px 16px',
        borderRadius: '12px',
        fontSize: store.fontSize + 'px',
      },
    },
    user: {
      bubble: {
        backgroundColor: 'var(--q-primary)',
        color: 'var(--q-text-main)',
      },
    },
    ai: {
      bubble: {
        backgroundColor: 'var(--q-fourth)',
        color: 'var(--q-text-main)',
      },
    },
  },
}));

const avatars = computed(() => {
  // Helper to create valid SVG data URI
  const createAvatarSvg = (text: string, bgColor: string, textColor: string) => {
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" fill="${bgColor}"/>
        <text x="50" y="50" font-family="Arial, sans-serif" font-size="50" fill="${textColor}" text-anchor="middle" dy=".35em">${text}</text>
      </svg>
    `.trim();
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const config: any = {
    default: {
      styles: {
        avatar: {
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          objectFit: 'cover',
        },
        container: {
          marginLeft: '10px',
          marginRight: '10px',
        },
      },
    },
  };

  // User Avatar
  if (authStore.user) {
    if (authStore.user.avatar_url) {
      let src = authStore.user.avatar_url;
      // Prepend API base URL if it's a relative path
      if (!src.startsWith('http') && !src.startsWith('blob:') && !src.startsWith('data:')) {
        const baseUrl = api.defaults.baseURL || '';
        src = `${baseUrl}${src.startsWith('/') ? '' : '/'}${src}`;
      }

      const position =
        typeof authStore.user.avatar_vertical_position === 'number'
          ? authStore.user.avatar_vertical_position
          : 50;

      config.user = {
        src: src,
        styles: {
          avatar: {
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            objectFit: 'cover',
            objectPosition: `center ${position}%`,
          },
        },
      };
    } else {
      // Generate fallback for user if no image
      const initials = (
        authStore.user.first_name?.[0] ||
        authStore.user.email?.[0] ||
        'U'
      ).toUpperCase();
      config.user = {
        src: createAvatarSvg(initials, 'var(--q-primary)', 'var(--q-text-main)'),
        styles: {
          avatar: {
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            objectFit: 'cover',
          },
        },
      };
    }
  }

  // Assistant Avatar
  if (props.assistant) {
    let src = '';

    if (blobAvatarUrl.value) {
      src = blobAvatarUrl.value;
    } else if (props.assistant.avatar_image) {
      // Fallback/Loading state: keep empty or show placeholder?
      // For DeepChat, empty src might show nothing.
      // We wait for blob.
      src = '';
    } else {
      // Generate fallback for assistant
      const name = props.assistant.name || 'AI';
      const initial = name.charAt(0).toUpperCase();
      const bgColor = props.assistant.avatar_bg_color || '#1976D2'; // Default blue if missing
      const textColor = props.assistant.avatar_text_color || '#FFFFFF';

      src = createAvatarSvg(initial, bgColor, textColor);
    }

    const aiPosition =
      typeof props.assistant.avatar_vertical_position === 'number'
        ? props.assistant.avatar_vertical_position
        : 50;

    config.ai = {
      src: src,
      styles: {
        avatar: {
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          objectFit: 'cover',
          objectPosition: `center ${aiPosition}%`,
        },
      },
    };
  }

  return config;
});

const blobAvatarUrl = ref<string | null>(null);

watch(
  [() => props.assistant?.id, () => props.assistant?.avatar_image],
  async ([newId, newImage]) => {
    // Cleanup old
    if (blobAvatarUrl.value) {
      URL.revokeObjectURL(blobAvatarUrl.value);
      blobAvatarUrl.value = null;
    }

    if (newId && newImage) {
      try {
        const blob = await assistantService.getAvatarBlob(newId);
        blobAvatarUrl.value = URL.createObjectURL(blob);
      } catch (e) {
        console.error('DeepChatWrapper: Failed to load avatar blob', e);
      }
    }
  },
  { immediate: true },
);

// Cleanup on unmount
onUnmounted(() => {
  if (blobAvatarUrl.value) {
    URL.revokeObjectURL(blobAvatarUrl.value);
  }
});

watch(
  avatars,
  (newAvatars) => {
    if (deepChatRef.value) {
      deepChatRef.value.avatars = newAvatars;
    }
  },
  { immediate: true, deep: true },
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const textInput = ref<any>({
  placeholder: { text: t('typeMessage') },
  styles: {
    container: {
      backgroundColor: 'var(--q-fourth)',
      borderRadius: '20px',
      border: 'none',
      outline: 'none',
      boxShadow: 'none',
      overflow: 'hidden',
    },
    text: {
      color: 'var(--q-text-main)',
      backgroundColor: 'var(--q-fourth)',
      borderRadius: '24px',
      padding: '12px 50px 12px 48px', // Right 50px for send, Left 48px for mic
      border: 'none',
      outline: 'none',
    },
  },
});

watch(
  () => props.disabled,
  (isDisabled) => {
    textInput.value = {
      ...textInput.value,
      disabled: isDisabled,
      placeholder: {
        text: isDisabled ? t('chatDisabledPlaceholder') : t('typeMessage'),
      },
      styles: {
        ...textInput.value.styles,
        container: {
          ...textInput.value.styles.container,
          opacity: isDisabled ? 0.6 : 1,
        },
      },
    };
  },
  { immediate: true },
);

const submitButtonStyles = computed(() => ({
  position: 'inside-end',
  submit: {
    container: {
      default: {
        position: 'absolute',
        right: '12px',
        top: '50%',
        transform: 'translateY(-50%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1,
        cursor: 'pointer',
      },
    },
    svg: {
      content: `<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="${$q.dark.isActive ? '#e8eaed' : '#757575'}"><path d="M120-160v-240l320-80-320-80v-240l760 320-760 320Z"/></svg>`,
      styles: {
        default: {
          width: '1.5em',
          height: '1.5em',
          fill: $q.dark.isActive ? '#e8eaed' : '#757575',
          filter: 'none',
          color: $q.dark.isActive ? '#e8eaed' : '#757575',
        },
      },
    },
  },
  disabled: {
    container: {
      default: { opacity: 1 },
    },
    svg: {
      styles: { default: {} },
    },
  },
  loading: {
    container: {
      default: { opacity: 0.6 },
    },
    svg: {
      styles: { default: {} },
    },
  },
}));

const introMessage = computed(() => {
  if (!props.assistant) return undefined;

  return {
    text: `Hello! I am ${props.assistant.name}.\n${props.assistant.description || 'How can I help you today?'}`,
    role: 'ai',
  };
});

const languageMap: Record<string, string> = {
  fr: 'fr-FR',
  'en-US': 'en-US',
};

const sttLanguage = computed(() => {
  const currentLocale = locale.value || 'en-US';
  return languageMap[currentLocale] || currentLocale;
});

const speechToTextConfig = computed(() => ({
  webSpeech: true, // Uses the browser's native Speech Recognition API
  language: sttLanguage.value,
  button: {
    position: 'inside-start', // Clean positioning inside the input
    default: {
      svg: {
        content: `<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="${$q.dark.isActive ? '#e8eaed' : '#757575'}"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 3.01-2.55 5.49-5.5 5.5S6 14.01 6 11H4c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>`,
        styles: {
          default: {
            width: '1.5em',
            height: '1.5em',
            fill: $q.dark.isActive ? '#e8eaed' : '#757575', // Explicitly set fill in style
            filter: 'none', // Ensure color is not affected by default filters
            color: $q.dark.isActive ? '#e8eaed' : '#757575',
            pointerEvents: 'none',
          },
        },
      },
      container: {
        default: {
          position: 'absolute',
          left: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: 1,
          width: '24px',
          height: '24px',
          cursor: 'pointer',
          zIndex: 10,
          pointerEvents: 'auto',
        },
      },
    },
    active: {
      svg: {
        content: `<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="${$q.dark.isActive ? '#e8eaed' : '#757575'}"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 3.01-2.55 5.49-5.5 5.5S6 14.01 6 11H4c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>`,
        styles: {
          default: {
            width: '1.5em',
            height: '1.5em',
            fill: $q.dark.isActive ? '#e8eaed' : '#757575',
            filter: 'none',
            color: $q.dark.isActive ? '#e8eaed' : '#757575',
            pointerEvents: 'none',
          },
        },
      },
      container: {
        default: {
          position: 'absolute',
          left: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: 1,
          width: '24px',
          height: '24px',
          cursor: 'pointer',
          zIndex: 10,
          pointerEvents: 'auto',
        },
      },
    },
    disabled: {
      svg: { styles: { default: {} } },
      container: { default: { opacity: 0.4 } },
    },
  },
}));

// --- Types ---

interface DeepChatSignals {
  onResponse: (payload: { text?: string; html?: string; role?: string }, isFinal?: boolean) => void;
  onOpen?: () => void;
  onClose?: () => void;
  stop?: () => void;
  end?: () => void;
  [key: string]: unknown;
}

interface DeepChatHandlerBody {
  messages?: Array<{ text?: string; role?: string }>;
}

interface ChartSeries {
  name: string;
  data: unknown[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

const activeSignals = shallowRef<DeepChatSignals | null>(null);
const hasStreamOpened = ref(false);

const connectConfig = {
  stream: true,
  handler: (body: DeepChatHandlerBody, signals: DeepChatSignals) => {
    // CRITICAL FIX: Close any previous stream before starting a new one
    // This ensures DeepChat creates a NEW bot message bubble instead of reusing the last one
    const previousSignals = activeSignals.value ? toRaw(activeSignals.value) : null;
    if (previousSignals) {
      console.log('[DeepChatWrapper] Closing previous stream before starting new request');
      try {
        if (previousSignals.stop) previousSignals.stop();
        if (previousSignals.end) previousSignals.end();
        if (previousSignals.onClose) previousSignals.onClose();
      } catch (err) {
        console.warn('[DeepChatWrapper] Error closing previous stream:', err);
      }
    }

    // Reset stream state for the new request
    activeSignals.value = signals;
    hasStreamOpened.value = false;

    if (body && body.messages && body.messages.length > 0) {
      const text = body.messages[0]?.text;
      if (text) emit('message-sent', text);
    }
  },
};

// --- Bridge Methods ---

/**
 * Adds a message to the Deep Chat UI
 * This is called by the parent to inject messages arriving from SSE or History
 */
const addMessage = (message: { role: string; text?: string; html?: string; error?: string }) => {
  if (deepChatRef.value) {
    deepChatRef.value.addMessage(message);
  }
};

/**
 * Streams a response using Deep Chat signals
 */
const streamResponse = (
  content: { text?: string; html?: string; role?: string },
  isFinal = false,
) => {
  console.log('[DeepChatWrapper] streamResponse called with:', {
    hasText: !!content.text,
    hasHtml: !!content.html,
    htmlLength: content.html?.length,
    textLength: content.text?.length,
    isFinal,
  });

  const signals = activeSignals.value ? toRaw(activeSignals.value) : null;

  if (signals) {
    // Ensure we signal that the stream is open on the first chunk
    if (!hasStreamOpened.value) {
      console.log('[DeepChatWrapper] Opening stream (onOpen)');
      if (signals.onOpen) signals.onOpen();
      hasStreamOpened.value = true;
    }

    const responsePayload: { text?: string; html?: string; role?: string } = {};
    if (content.text) responsePayload.text = content.text;
    if (content.html) responsePayload.html = content.html;

    try {
      // Send chunk
      if (Object.keys(responsePayload).length > 0) {
        console.log('[DeepChatWrapper] Calling signals.onResponse with:', {
          hasText: !!responsePayload.text,
          hasHtml: !!responsePayload.html,
          isFinal,
        });
        // If it is final, we pass 'true' here to signal Deep Chat to close the stream logic internally
        signals.onResponse(responsePayload, isFinal);
      } else if (isFinal) {
        // If final but empty payload, we still need to signal completion
        console.log('[DeepChatWrapper] Calling signals.onResponse with empty payload (final)');
        signals.onResponse({ text: '' }, true);
      }

      if (isFinal) {
        console.log('[DeepChatWrapper] Stream is final, closing signals');
        // Explicitly close the stream callbacks if defined
        if (signals.stop) signals.stop();
        if (signals.end) signals.end(); // Some versions might use end()
        if (signals.onClose) signals.onClose();

        activeSignals.value = null;
        hasStreamOpened.value = false;
      }
    } catch (err) {
      console.error('DeepChatWrapper: Error calling onResponse:', err);
    }
  } else {
    console.warn('DeepChatWrapper: Stream requested but no active signals.', content);
  }
};

/**
 * Appends HTML to the last bot message
 * This is used to add steps/sources/visualization after streaming completes
 */
const appendToLastMessage = (html: string) => {
  console.log('[DeepChatWrapper] appendToLastMessage called with HTML length:', html.length);

  // 1. Get the Safe Reference
  const deepChatElement = deepChatRef.value as HTMLElement;
  if (!deepChatElement) {
    console.error('[DeepChatWrapper] deepChatRef is null!');
    return;
  }

  try {
    // 2. Safe Access to Shadow DOM
    const shadowRoot = deepChatElement.shadowRoot;
    if (!shadowRoot) {
      console.error('[DeepChatWrapper] No shadow root found on deep-chat element!');
      return;
    }

    // 3. Find the container (standard Deep Chat structure)
    const messagesContainer = shadowRoot.getElementById('container');
    if (!messagesContainer) {
      console.error('[DeepChatWrapper] #container not found in Shadow DOM');
      return;
    }

    // 4. Find the last AI message bubble
    const messageBubbles = messagesContainer.querySelectorAll('.message-bubble');
    if (messageBubbles.length === 0) {
      console.error('[DeepChatWrapper] No message bubbles found');
      return;
    }

    // Iterate backwards to find the last AI message
    let lastBubble: HTMLElement | null = null;
    for (let i = messageBubbles.length - 1; i >= 0; i--) {
      const bubble = messageBubbles[i] as HTMLElement;
      if (bubble.classList.contains('ai-message')) {
        lastBubble = bubble;
        break;
      }
    }

    if (!lastBubble) {
      console.warn('[DeepChatWrapper] No AI message bubble found to append content to');
      return;
    }

    // 6. Find the content area valid in DeepChat structure
    // We prefer appending to the text content specifically if it exists, otherwise the bubble itself
    const contentArea = lastBubble.querySelector('.text-message, .message-content') || lastBubble;

    // 7. Create a wrapper for our new content to ensuring clean separation
    const newContentWrapper = document.createElement('div');
    newContentWrapper.className = 'vectra-injected-content';
    newContentWrapper.style.marginTop = '10px';
    newContentWrapper.innerHTML = html;

    // 8. Append safely
    contentArea.appendChild(newContentWrapper);
    console.log('[DeepChatWrapper] Successfully appended content to last message bubble');
  } catch (err) {
    console.error('[DeepChatWrapper] Error in appendToLastMessage:', err);
  }
};

// --- Event Handlers ---

// --- Chart Hydration Logic ---

const pendingCharts = new Map<string, any>(); // eslint-disable-line @typescript-eslint/no-explicit-any
let chartObserver: MutationObserver | null = null;
const observerTargetConfig = { childList: true, subtree: true };

/**
 * Registers a chart configuration to be hydrated once the DOM element appears
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const registerChart = (chartId: string, config: any) => {
  pendingCharts.set(chartId, config);
};

/**
 * Immediately hydrates a chart that's already in the DOM
 * Used after appending HTML via appendToLastMessage
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const hydrateChartNow = (chartId: string, config: any) => {
  console.log('[DeepChatWrapper] hydrateChartNow called for:', chartId);

  if (!deepChatRef.value) {
    console.error('[DeepChatWrapper] deepChatRef is null!');
    return;
  }

  const shadowRoot = deepChatRef.value.shadowRoot;
  if (!shadowRoot) {
    console.error('[DeepChatWrapper] No shadow root!');
    return;
  }

  // Find the chart element in the Shadow DOM
  const chartElement = shadowRoot.querySelector(`#${chartId}`);
  if (!chartElement) {
    console.warn(
      `[DeepChatWrapper] hydrateChartNow: Chart element #${chartId} not found. Fallback to registration.`,
    );
    // Fallback: Register for MutationObserver to pick it up when rendered
    registerChart(chartId, config);
    return;
  }

  console.log('[DeepChatWrapper] Found chart element, hydrating...');
  hydrateChart(chartElement, config);
};

onMounted(() => {
  // ... (omitted comments for brevity, keeping existing structure logic)
  const nativeElement = deepChatRef.value; // Accessing the DOM element
  if (!nativeElement) return;

  const shadowRoot = nativeElement.shadowRoot;
  const target = shadowRoot || nativeElement;

  chartObserver = new MutationObserver(() => {
    // Optimized: Check if we have pending charts first
    if (pendingCharts.size === 0) return;

    pendingCharts.forEach((config, id) => {
      const element = target.querySelector(`#${id}`);
      if (element) {
        console.log(`DeepChatWrapper: Hydrating chart ${id}`);
        hydrateChart(element, config);
        pendingCharts.delete(id);
      }
    });
  });

  chartObserver.observe(target, observerTargetConfig);
});

onUnmounted(() => {
  if (chartObserver) {
    chartObserver.disconnect();
  }
  pendingCharts.clear();
});

import ApexCharts, { type ApexOptions } from 'apexcharts';

const hydrateChart = (element: Element, config: ApexOptions & { viz_type?: string }) => {
  // Clear loading placeholder
  element.innerHTML = '';

  // Defensive: Ensure config has required structure
  if (!config || typeof config !== 'object') {
    console.error('DeepChatWrapper: Invalid chart config', config);
    element.innerHTML = '<div style="color: red;">Invalid chart configuration</div>';
    return;
  }

  // Build complete configuration with proper defaults
  // Important: Provide ALL nested objects with complete defaults that ApexCharts might access

  console.log('[DeepChatWrapper] Hydrating chart with config:', {
    chartType: config.chart?.type,
    vizType: config.viz_type,
    seriesType: typeof config.series,
    seriesIsArray: Array.isArray(config.series),
    seriesLength: config.series?.length,
    firstElement: config.series?.[0],
    firstElementType: typeof config.series?.[0],
  });

  // Handle series properly - could be array of primitives (circular charts) or array of objects (cartesian charts)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let processedSeries: any[];
  if (Array.isArray(config.series) && config.series.length > 0) {
    // Check if the first element is a primitive (number) or an object
    const firstElement = config.series[0];
    if (typeof firstElement === 'number' || typeof firstElement === 'string') {
      // Circular chart format: [15000, 20000, ...]
      console.log('[DeepChatWrapper] Detected primitive series (circular chart)');
      processedSeries = config.series;
    } else {
      // Cartesian/Treemap format: [{name: "...", data: [...]}, ...]
      console.log('[DeepChatWrapper] Detected object series (cartesian/treemap)');
      // Cast element to ChartSeries to satisfy TS, as ApexAxisChartSeries is strict
      processedSeries = (config.series as ChartSeries[]).map((s) => ({
        ...s,
        data: s.data || [],
      }));
    }
  } else {
    processedSeries = [];
  }

  // console.log('[DeepChatWrapper] Processed series:', JSON.stringify(processedSeries, null, 2));

  // Determine theme mode from Quasar
  const themeMode = $q.dark.isActive ? 'dark' : 'light';
  console.log('[DeepChatWrapper] Hydrating chart with theme mode:', themeMode);

  const chartConfig = {
    series: processedSeries,
    labels: config.labels || config.xaxis?.categories || [],
    chart: {
      type: config.chart?.type || config.viz_type || 'bar',
      background: 'transparent',
      width: '100%',
      height: 300,
      toolbar: { show: false },
      fontFamily: 'inherit',
      ...(config.chart || {}),
    },
    theme: {
      mode: themeMode,
      ...(config.theme || {}),
    },
    dataLabels: {
      enabled: true,
      style: {},
      background: {},
      dropShadow: {},
      ...(config.dataLabels || {}),
    },
    plotOptions: config.plotOptions || {},
    legend: {
      show: true,
      position: 'bottom',
      horizontalAlign: 'center',
      floating: false,
      fontSize: '14px',
      fontFamily: 'inherit',
      fontWeight: 400,
      labels: {},
      markers: {},
      itemMargin: {},
      onItemClick: {},
      onItemHover: {},
      ...(config.legend || {}),
    },
    xaxis: {
      labels: {},
      axisBorder: {},
      axisTicks: {},
      ...(config.xaxis || {}),
    },
    yaxis: {
      labels: {},
      title: {},
      axisBorder: {},
      axisTicks: {},
      ...(config.yaxis || {}),
    },
    colors: config.colors || undefined,
    // Ensure title and subtitle are properly structured objects or omitted
    ...(config.title && typeof config.title === 'object' ? { title: config.title } : {}),
    ...(config.subtitle && typeof config.subtitle === 'object'
      ? { subtitle: config.subtitle }
      : {}),
  };

  // Special handling for Funnel charts
  // ApexCharts 'funnel' type can be flaky with certain data formats.
  // We force it to 'bar' with useFunnel: true (or isFunnel: true depending on version, usually part of bar options)
  if (chartConfig.chart.type === 'funnel') {
    console.log('[DeepChatWrapper] Converting funnel chart to bar + isFunnel');
    chartConfig.chart.type = 'bar';
    if (!chartConfig.plotOptions.bar) {
      chartConfig.plotOptions.bar = {};
    }
    // Force horizontal and proper bar settings for funnel
    chartConfig.plotOptions.bar = {
      ...chartConfig.plotOptions.bar,
      horizontal: true,
      barHeight: '80%',
      isFunnel: true,
      borderRadius: 0,
      distributed: true, // 👈 Enable distributed colors for "3D"/multi-color look
    };
  }

  try {
    const chart = new ApexCharts(element, chartConfig);
    void chart.render();

    // Store active chart instance for dynamic updates
    if (element.id) {
      activeCharts.set(element.id, chart);
    }
  } catch (err) {
    console.error('DeepChatWrapper: Chart rendering failed', err, config);
    element.innerHTML =
      '<div style="color: red; padding: 12px;">Chart rendering failed. Please try again.</div>';
  }
};

// --- Dynamic Theme Switching ---

// Track active chart instances to update them when theme changes
// Key: element ID, Value: ApexCharts instance
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const activeCharts = new Map<string, any>();

watch(
  () => $q.dark.isActive,
  (isDark) => {
    console.log('[DeepChatWrapper] Theme changed, updating charts to:', isDark ? 'dark' : 'light');
    activeCharts.forEach((chart, id) => {
      try {
        console.log(`[DeepChatWrapper] Updating theme for chart ${id}`);
        chart.updateOptions({
          theme: {
            mode: isDark ? 'dark' : 'light',
          },
        });
      } catch (err) {
        console.error(`[DeepChatWrapper] Failed to update theme for chart ${id}:`, err);
        // If update fails (e.g., chart destroyed), remove from map
        activeCharts.delete(id);
      }
    });
  },
);

// Clean up charts on unmount - this is separate from chartObserver
// We need to ensure we don't leak ApexCharts instances
import { onBeforeUnmount } from 'vue';

onBeforeUnmount(() => {
  activeCharts.forEach((chart) => {
    try {
      chart.destroy();
    } catch {
      /* ignore */
    }
  });
  activeCharts.clear();
});

const clearHistory = () => {
  if (deepChatRef.value) {
    deepChatRef.value.history = [];
  }
  // Clear pending charts to prevent NaN errors on reset
  pendingCharts.clear();
};

// --- Expose with new methods ---

const setHistory = (history: unknown[]) => {
  if (deepChatRef.value) {
    // Determine if we need to clear first or just overwrite
    // Overwriting is safer
    deepChatRef.value.history = history;
    console.log(`[DeepChatWrapper] setHistory called with ${history.length} messages`);
  }
  // DO NOT clear pending charts here. They are registered via prepareMessagePayload BEFORE setHistory is called.
  // Clearing them here wipes the registry just before the Observer needs them.
};

const setInputText = (text: string) => {
  console.log('[DeepChatWrapper] setInputText called with:', text);

  if (!deepChatRef.value) return;

  const element = deepChatRef.value as HTMLElement;
  const shadowRoot = element.shadowRoot;

  if (!shadowRoot) {
    console.warn('[DeepChatWrapper] No shadow root found for setInputText');
    return;
  }

  // Attempt to find the input element (contenteditable div or textarea/input)
  // Deep Chat usually uses a contenteditable div for rich text support
  const inputEl = shadowRoot.querySelector(
    'div[contenteditable="true"], input[type="text"], textarea',
  ) as HTMLElement;

  if (inputEl) {
    console.log('[DeepChatWrapper] Found input element, setting text directly');

    // Clear first to be safe
    inputEl.textContent = text;

    // For input/textarea, also set value
    if (inputEl instanceof HTMLInputElement || inputEl instanceof HTMLTextAreaElement) {
      inputEl.value = text;
    }

    // Dispatch input event to trigger internal state updates in Deep Chat
    inputEl.dispatchEvent(new Event('input', { bubbles: true, composed: true }));

    // Move cursor to end (UX polish)
    inputEl.focus();
    const range = document.createRange();
    range.selectNodeContents(inputEl);
    range.collapse(false);
    const sel = window.getSelection();
    if (sel) {
      sel.removeAllRanges();
      sel.addRange(range);
    }
  } else {
    console.warn('[DeepChatWrapper] Could not find input element in Shadow DOM');
    // Fallback to the hybrid prop method (though it likely failed before, we keep it as backup)
    const newConfig = {
      ...textInput.value,
      state: { text },
    };
    textInput.value = newConfig;
    deepChatRef.value.textInput = newConfig;
  }
};

defineExpose({
  addMessage,
  streamResponse,
  appendToLastMessage,
  registerChart,
  hydrateChartNow,
  clearHistory,
  setHistory,
  setInputText, // Expose new method
  getNativeElement: () => deepChatRef.value,
});
</script>

<style scoped>
.deep-chat-container {
  width: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Force submit button inside the input container */
.deep-chat-container :deep(deep-chat) {
  --submit-button-position: absolute !important;
}
</style>

<style>
/* Global styles to override deep-chat shadow DOM */
deep-chat::part(submit-button) {
  position: absolute !important;
  right: 12px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  z-index: 10 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
</style>
