<template>
  <teleport to="#chat-header-portal" v-if="assistant">
    <div class="row items-center q-gutter-x-sm">
      <AssistantAvatar v-if="assistant" :assistant="assistant" size="32px" />
      <span class="text-h6 text-white text-weight-bold">{{ assistant.name }}</span>

      <q-space />
    </div>
  </teleport>
</template>

<script setup lang="ts">
import type { Assistant } from 'src/services/assistantService';
import AssistantAvatar from 'components/assistants/AssistantAvatar.vue';

defineProps<{
  assistantId?: string;
  assistant: Assistant | null;
}>();
</script>
