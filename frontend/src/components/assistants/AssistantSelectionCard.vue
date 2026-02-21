<template>
  <q-card
    flat
    class="assistant-selection-card column full-height clickable"
    @click="$emit('select')"
    :style="cardStyle"
  >
    <!-- Background Glow -->
    <div class="glow-overlay" :style="glowStyle"></div>

    <q-card-section class="col column items-center q-pa-xl relative-position">
      <!-- Avatar with Ring -->
      <div class="avatar-ring" :style="{ borderColor: assistant.avatar_bg_color || 'var(--q-accent)' }">
        <AssistantAvatar
          :assistant="assistant"
          size="100px"
          class="assistant-avatar-main"
        />
      </div>

      <!-- Name & Badge -->
      <div class="text-h5 text-weight-bolder text-white q-mt-lg q-mb-xs assistant-name">
        {{ assistant.name }}
      </div>

      <!-- Model Pill -->
      <div class="model-pill q-mb-md">
        <q-icon name="bolt" size="14px" class="q-mr-xs" />
        {{ assistant.model || 'Gemini' }}
      </div>

      <!-- Description (Optional) -->
      <div v-if="assistant.description" class="description-text q-mb-lg text-center">
        {{ assistant.description }}
      </div>

      <!-- Stats / Metadata -->
      <div class="metadata-row row items-center justify-center q-gutter-x-md opacity-60">
        <div class="row items-center q-gutter-x-xs">
          <q-icon name="folder" size="16px" />
          <span class="text-caption font-weight-medium">
            {{ connectorCount }} {{ $t('connectedSources') }}
          </span>
        </div>
      </div>

      <!-- Tags Section -->
      <div v-if="tags.length > 0" class="tags-container q-mt-lg">
        <div class="row justify-center q-gutter-xs">
          <q-chip
            v-for="tag in tags.slice(0, 2)"
            :key="tag"
            :label="tag"
            size="sm"
            outline
            class="tag-chip"
          />
          <q-chip
            v-if="tags.length > 2"
            :label="`+${tags.length - 2}`"
            size="sm"
            outline
            class="tag-chip more"
          />
        </div>
      </div>
    </q-card-section>

    <!-- Action Section Integrated -->
    <div class="action-footer q-pa-md row justify-center">
      <div class="action-btn-styled">
        <q-icon name="chat" size="20px" class="q-mr-sm" />
        {{ $t('startChatting') }}
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AssistantAvatar from 'src/components/assistants/AssistantAvatar.vue';
import type { Assistant } from 'src/services/assistantService';

const props = defineProps<{
  assistant: Assistant;
}>();

defineEmits(['select']);

const connectorCount = computed(() => {
  return (props.assistant.linked_connectors?.length || props.assistant.linked_connector_ids?.length || 0);
});

const tags = computed(() => {
  return props.assistant.configuration?.tags || [];
});

const cardStyle = computed(() => {
  return {
    '--assistant-color': props.assistant.avatar_bg_color || 'var(--q-accent)'
  };
});

const glowStyle = computed(() => {
  return {
    background: `radial-gradient(circle at 50% 0%, ${props.assistant.avatar_bg_color || 'var(--q-accent)'}20 0%, transparent 70%)`
  };
});
</script>

<style scoped>
.assistant-selection-card {
  background: linear-gradient(145deg, var(--q-secondary) 0%, rgba(var(--q-secondary-rgb), 0.8) 100%);
  border: 1px solid var(--q-third);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.glow-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  pointer-events: none;
  opacity: 0.5;
  transition: opacity 0.4s ease;
}

.assistant-selection-card:hover {
  transform: translateY(-8px);
  border-color: var(--q-sixth);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.assistant-selection-card:hover .glow-overlay {
  opacity: 1;
}

.avatar-ring {
  padding: 6px;
  border: 2px solid;
  border-radius: 50%;
  transition: all 0.4s ease;
  background: rgba(255, 255, 255, 0.03);
}

.assistant-selection-card:hover .avatar-ring {
  transform: scale(1.1) rotate(5deg);
}

.assistant-name {
  letter-spacing: -0.01em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.model-pill {
  background: rgba(var(--q-accent-rgb), 0.1);
  border: 1px solid rgba(var(--q-accent-rgb), 0.2);
  color: var(--assistant-color);
  padding: 2px 12px;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.description-text {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--q-text-sub);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-width: 250px;
  opacity: 0.9;
}

.tag-chip {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: rgba(255, 255, 255, 0.6) !important;
  font-weight: 600;
}

.tag-chip.more {
  border-style: dashed !important;
}

.action-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.assistant-selection-card:hover .action-footer {
  background: rgba(255, 255, 255, 0.03);
}

.action-btn-styled {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 12px;
  font-weight: 700;
  color: white;
  transition: all 0.3s ease;
  letter-spacing: 0.02em;
}

.assistant-selection-card:hover .action-btn-styled {
  color: var(--assistant-color);
}
</style>
