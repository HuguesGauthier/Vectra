<template>
  <q-avatar
    :size="size"
    :style="avatarStyle"
    :text-color="textColor"
    class="assistant-avatar"
  >
    <img
      v-if="blobUrl"
      :src="blobUrl"
      class="avatar-image"
      :style="{ objectPosition: `center ${assistant.avatar_vertical_position ?? 50}%` }"
    />
    <q-icon v-else name="psychology" />
  </q-avatar>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue';
import type { Assistant } from 'src/services/assistantService';
import { assistantService } from 'src/services/assistantService';

const props = withDefaults(
  defineProps<{
    assistant: Assistant;
    size?: string;
    refreshKey?: number | string;
  }>(),
  {
    size: 'md',
    refreshKey: 0,
  }
);

const blobUrl = ref<string | null>(null);

const textColor = computed(() => props.assistant.avatar_text_color || 'white');

const avatarStyle = computed(() => {
  const bgColor = props.assistant.avatar_bg_color;
  if (!bgColor) return { backgroundColor: 'var(--q-primary)' };
  return { backgroundColor: bgColor };
});

watch(
  [() => props.assistant.id, () => props.assistant.avatar_image, () => props.refreshKey],
  async ([newId, newImage]) => {
    // Revoke old URL if exists
    if (blobUrl.value) {
      URL.revokeObjectURL(blobUrl.value);
      blobUrl.value = null;
    }

    if (newImage && newId) {
      try {
        const blob = await assistantService.getAvatarBlob(newId);
        blobUrl.value = URL.createObjectURL(blob);
      } catch {
        // Silent fail
      }
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (blobUrl.value) {
    URL.revokeObjectURL(blobUrl.value);
  }
});
</script>

<style scoped>
.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
