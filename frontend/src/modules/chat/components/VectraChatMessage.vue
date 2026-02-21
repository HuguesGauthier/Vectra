<template>
  <div class="message-row row q-mb-md" :class="isUser ? 'justify-end' : 'justify-start'">
    <!-- AI Avatar -->
    <q-avatar
      v-if="!isUser"
      size="40px"
      class="q-mr-sm shadow-2 self-end q-mb-xs"
      :style="{ backgroundColor: assistant?.avatar_bg_color || 'var(--q-primary)' }"
    >
      <img v-if="assistantAvatarUrl" :src="assistantAvatarUrl" />
      <span v-else class="text-subtitle1 text-white">{{ assistantInitials }}</span>
    </q-avatar>

    <!-- Message Bubble -->
    <div
      class="message-bubble q-pa-md shadow-2 relative-position"
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
    <q-avatar v-if="isUser" size="40px" class="q-ml-sm shadow-2 self-end q-mb-xs bg-grey-8">
      <img v-if="userAvatarUrl" :src="userAvatarUrl" />
      <q-icon v-else name="person" color="white" />
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
  if (!baseColor) return {};

  // Basic hex to rgba conversion for the gradient
  const hex = baseColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16) || 0;
  const g = parseInt(hex.substring(2, 4), 16) || 0;
  const b = parseInt(hex.substring(4, 6), 16) || 0;

  // Create a beautiful pure glass/gradient effect with the selected color
  return {
    background: `linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 0.15) 0%, rgba(${r}, ${g}, ${b}, 0.05) 100%)`,
    borderColor: `rgba(${r}, ${g}, ${b}, 0.2)`,
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
  border-radius: 18px;
  line-height: var(--chat-font-size, 1.5);
  font-size: 1em; /* Inherit from VectraChat --chat-font-size */
  transition: all 0.3s ease;
  word-wrap: break-word;
}

.user-bubble {
  background: var(--q-primary);
  color: var(--q-text-main);
  border-bottom-right-radius: 4px;
}

.ai-bubble {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--q-text-main);
  border-bottom-left-radius: 4px;
}

.ai-bubble:hover {
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
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
  color: white;
  text-decoration: underline;
}

::v-deep(.ai-bubble .markdown-content a) {
  color: #64b5f6;
  text-decoration: none;
}
::v-deep(.ai-bubble .markdown-content a:hover) {
  text-decoration: underline;
}
</style>
