<template>
  <div class="message-row row q-mb-md" :class="isUser ? 'justify-end' : 'justify-start'">
    <!-- AI Avatar -->
    <q-avatar
      v-if="!isUser"
      size="28px"
      class="q-mr-sm self-end"
      :style="{ backgroundColor: assistant?.avatar_bg_color || 'var(--q-primary)' }"
    >
      <img v-if="assistantAvatarUrl" :src="assistantAvatarUrl" />
      <span v-else class="text-caption text-weight-bold text-white">{{ assistantInitials }}</span>
    </q-avatar>

    <!-- Message Bubble -->
    <div
      class="message-bubble q-pa-md relative-position"
      :class="{
        'user-bubble': isUser,
        'ai-bubble': !isUser,
        'has-error': hasError,
      }"
      :style="aiBubbleStyle"
    >
      <!-- Text Content (Rendered Markdown) -->
      <div
        v-if="renderedMarkdown"
        class="markdown-content text-body1"
        v-html="renderedMarkdown"
      ></div>

      <!-- Blocks -->
      <template v-if="message.contentBlocks && message.contentBlocks.length">
        <div
          v-for="(block, index) in contentBlocksWithoutText"
          :key="`block-${index}`"
          class="q-mt-md"
        >
          <VectraTechSheet v-if="block.type === 'tech-sheet'" :data="block.data as any" />
          <VectraDataTable v-else-if="block.type === 'table'" :data="block.data" />
        </div>
      </template>

      <!-- Visualization (ApexCharts) -->
      <VectraVisualization
        v-if="message.visualization"
        :config="message.visualization"
        class="q-mt-md"
      />

      <!-- Steps (Pipeline Reasoning) -->
      <VectraPipelineSteps
        v-if="message.steps && message.steps.length"
        :steps="message.steps"
        class="q-mt-sm"
      />

      <!-- Sources -->
      <VectraSources
        v-if="message.sources && message.sources.length"
        :sources="message.sources"
        class="q-mt-sm"
      />

      <!-- Error / Status Indicator -->
      <div v-if="hasError" class="text-negative q-mt-sm row items-center text-caption">
        <q-icon name="error_outline" class="q-mr-xs" />
        <!-- eslint-disable-next-line @typescript-eslint/no-explicit-any -->
        {{ (message as any).error || 'An error occurred' }}
      </div>
      <div
        v-else-if="message.statusMessage && !message.text"
        class="text-grey-5 q-mt-xs text-caption row items-center"
      >
        <q-spinner-dots size="1em" class="q-mr-xs" />
        {{ message.statusMessage }}
      </div>
    </div>

    <!-- User Avatar -->
    <q-avatar v-if="isUser" size="28px" class="q-ml-sm self-end bg-grey-8">
      <img v-if="userAvatarUrl" :src="userAvatarUrl" />
      <q-icon v-else name="person" color="white" size="18px" />
    </q-avatar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import MarkdownIt from 'markdown-it';
import { useAuthStore } from 'src/stores/authStore';
import { api } from 'boot/axios';
import type { ChatMessage, ContentBlock } from '../composables/useChatStream';
import type { Assistant } from 'src/services/assistantService';

import VectraTechSheet from './blocks/VectraTechSheet.vue';
import VectraDataTable from './blocks/VectraDataTable.vue';
import VectraPipelineSteps from './blocks/VectraPipelineSteps.vue';
import VectraSources from './blocks/VectraSources.vue';
import VectraVisualization from './blocks/VectraVisualization.vue';

const props = defineProps<{
  message: ChatMessage;
  assistant: Assistant | null;
  assistantAvatarUrl: string | null;
}>();

const authStore = useAuthStore();
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
});

// --- Computed ---

const isUser = computed(() => props.message.sender === 'user');
const hasError = computed(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const msgError = (props.message as any).error;
  return !!msgError || props.message.text.includes('Error:');
});

const userAvatarUrl = computed(() => {
  if (authStore.user?.avatar_url) {
    let src = authStore.user.avatar_url;
    if (!src.startsWith('http') && !src.startsWith('blob:') && !src.startsWith('data:')) {
      const baseUrl = api.defaults.baseURL || '';
      src = `${baseUrl}${src.startsWith('/') ? '' : '/'}${src}`;
    }
    return src;
  }
  return null;
});

const assistantInitials = computed(() => {
  return props.assistant?.name?.charAt(0).toUpperCase() || 'A';
});

// Calculate a dynamic gradient for the AI bubble if a color is present
const aiBubbleStyle = computed(() => {
  if (isUser.value || hasError.value) return {};

  const baseColor = props.assistant?.avatar_bg_color;
  if (!baseColor || !baseColor.startsWith('#')) {
    return { background: 'var(--q-primary)', color: 'white' };
  }

  // Basic hex to rgba conversion for the gradient
  const hex = baseColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16) || 0;
  const g = parseInt(hex.substring(2, 4), 16) || 0;
  const b = parseInt(hex.substring(4, 6), 16) || 0;

  // Base color darker variations for a rich, pure gradient
  const rD = Math.max(0, r - 50);
  const gD = Math.max(0, g - 50);
  const bD = Math.max(0, b - 50);

  // Determine if color is light or dark to adjust text color
  // YIQ formula
  const yiq = (r * 299 + g * 587 + b * 114) / 1000;
  const textColor = yiq >= 150 ? '#121212' : '#ffffff';

  // Create a beautiful pure gradient effect with the selected color
  return {
    background: `linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 1) 0%, rgba(${rD}, ${gD}, ${bD}, 1) 100%)`,
    color: textColor,
    boxShadow: `0 8px 24px rgba(${r}, ${g}, ${b}, 0.25)`,
    border: 'none',
  };
});

// We only render text blocks directly as markdown
const renderedMarkdown = computed(() => {
  // Try to find the first text block, or use message.text fallback
  const textBlock = props.message.contentBlocks?.find((b) => b.type === 'text');
  const textRaw = textBlock ? String(textBlock.data) : props.message.text;

  if (!textRaw) return '';
  return md.render(textRaw);
});

// Filter out text blocks since they are rendered above
const contentBlocksWithoutText = computed(() => {
  return props.message.contentBlocks?.filter((b: ContentBlock) => b.type !== 'text') || [];
});
</script>

<style scoped>
.message-bubble {
  max-width: 85%;
  line-height: var(--chat-font-size, 1.5);
  font-size: 1em; /* Inherit from VectraChat --chat-font-size */
  transition: all 0.3s ease;
  word-wrap: break-word;
  padding: 16px 20px;
}

.user-bubble {
  /* Clean frosted panel for the user, matching the screenshot's neutral tone */
  background: rgba(120, 120, 120, 0.15);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(120, 120, 120, 0.1);
  color: var(--q-text-main);
  border-radius: 20px 20px 4px 20px; /* Sharp bottom right */
}

.ai-bubble {
  border-radius: 20px 20px 20px 4px; /* Sharp bottom left */
}

/* Added slight spacing so the bubble visually rests above the avatar baseline */
.message-bubble {
  margin-bottom: 4px;
}

.has-error {
  border-color: rgba(244, 67, 54, 0.5) !important;
  background: rgba(244, 67, 54, 0.05) !important;
}

::v-deep(.markdown-content p:last-child) {
  margin-bottom: 0;
}

::v-deep(.markdown-content pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

::v-deep(.markdown-content code) {
  font-family: 'Courier New', Courier, monospace;
  background: rgba(0, 0, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

::v-deep(.user-bubble .markdown-content a) {
  color: var(--q-accent) !important;
  text-decoration: underline;
}

::v-deep(.ai-bubble .markdown-content a) {
  /* For vivid vibrant backgrounds, links need high contrast */
  color: inherit;
  text-decoration: underline;
  opacity: 0.9;
}
::v-deep(.ai-bubble .markdown-content a:hover) {
  opacity: 1;
}
</style>
