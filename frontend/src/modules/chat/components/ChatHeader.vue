<template>
  <teleport to="#chat-header-portal" v-if="assistant">
    <div class="row items-center q-gutter-x-sm">
      <q-avatar
        :color="!avatarUrl && assistant.avatar_bg_color ? assistant.avatar_bg_color : undefined"
        :style="
          !avatarUrl && assistant.avatar_bg_color
            ? { backgroundColor: assistant.avatar_bg_color }
            : {}
        "
        :text-color="assistant.avatar_text_color || 'white'"
        size="32px"
      >
        <img
          v-if="avatarUrl"
          :src="avatarUrl"
          style="object-fit: cover"
          :style="{ objectPosition: `center ${assistant.avatar_vertical_position ?? 50}%` }"
        />
        <q-icon v-else name="psychology" />
      </q-avatar>
      <span class="text-h6 text-white text-weight-bold">{{ assistant.name }}</span>

      <q-space />
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Assistant } from 'src/services/assistantService';
import { assistantService } from 'src/services/assistantService';

const props = defineProps<{
  assistantId?: string;
  assistant: Assistant | null;
}>();

const avatarUrl = computed(() => {
  if (props.assistant?.avatar_image && props.assistant?.id) {
    return assistantService.getAvatarUrl(props.assistant.id);
  }
  return null;
});
</script>
