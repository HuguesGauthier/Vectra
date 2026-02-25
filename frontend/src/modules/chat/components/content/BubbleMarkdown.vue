<template>
  <div
    class="markdown-content"
    v-html="renderMarkdown(data)"
    :style="{ fontSize: chatStore.fontSize + 'px' }"
  ></div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it';
import { usePublicChatStore } from 'src/stores/publicChatStore';

const chatStore = usePublicChatStore();

defineProps<{
  data: string;
}>();

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
});

function renderMarkdown(text: string) {
  if (!text) return '';
  return md.render(text);
}
</script>
