<template>
  <q-card
    flat
    class="assistant-selection-card column full-height clickable bg-primary"
    @click="$emit('select')"
    :style="cardStyle"
  >
    <div class="assistant-card-banner">
      <!-- Background Glow -->
      <div class="glow-overlay" :style="glowStyle"></div>

      <!-- Top Right Header Badges -->
      <div class="header-badges-vertical">
        <!-- Model Pill -->
        <div class="model-pill" :style="pillStyle">
          <q-img
            v-if="providerLogo"
            :src="providerLogo"
            width="12px"
            height="12px"
            class="q-mr-xs provider-logo"
            fit="contain"
          />
          <q-icon v-else name="bolt" size="12px" class="q-mr-xs" />
          {{ displayModelName }}
        </div>
      </div>
    </div>

    <q-card-section class="q-pt-none q-px-lg relative-position info-section">
      <!-- Avatar with Ring -->
      <div class="avatar-wrapper">
        <div
          class="avatar-ring"
          :style="{ borderColor: assistant.avatar_bg_color || 'var(--q-accent)' }"
        >
          <AssistantAvatar
            :assistant="assistant"
            size="80px"
            class="assistant-avatar-main shadow-5"
          />
        </div>
      </div>

      <!-- Identification Block -->
      <div class="column q-mt-sm">
        <div class="text-h6 text-weight-bolder assistant-name q-mb-xs">
          {{ assistant.name }}
        </div>

        <!-- Description (Optional) -->
        <div v-if="assistant.description" class="description-text q-mb-sm">
          {{ assistant.description }}
        </div>

        <!-- Tags Section -->
        <div v-if="tags.length > 0" class="tags-container q-mb-md">
          <div class="row q-gutter-xs">
            <q-badge v-for="tag in tags.slice(0, 3)" :key="tag" class="tag-badge">
              {{ tag }}
            </q-badge>
            <q-badge v-if="tags.length > 3" class="tag-badge more">
              +{{ tags.length - 3 }}
            </q-badge>
          </div>
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AssistantAvatar from 'src/components/assistants/AssistantAvatar.vue';
import type { Assistant } from 'src/services/assistantService';
import { useAiProviders } from 'src/composables/useAiProviders';

const props = defineProps<{
  assistant: Assistant;
}>();

defineEmits(['select']);

const { getProviderLogo, getProviderColor } = useAiProviders();

const providerLogo = computed(() => getProviderLogo(props.assistant.model_provider, 'chat'));
const providerColor = computed(() => getProviderColor(props.assistant.model_provider));

const displayModelName = computed(() => {
  if (props.assistant.model_provider?.toLowerCase() === 'ollama') {
    return 'Mistral';
  }
  return props.assistant.model || 'Gemini';
});

const tags = computed(() => {
  return props.assistant.configuration?.tags || [];
});

const pillStyle = computed(() => {
  const color = providerColor.value || 'grey-7';
  return {
    backgroundColor: `rgba(var(--q-${color}-rgb, 100, 100, 100), 0.12)`,
    backdropFilter: 'blur(4px)',
    border: `1px solid rgba(var(--q-${color}-rgb, 100, 100, 100), 0.25)`,
    color: `var(--q-${color})`,
  };
});

const cardStyle = computed(() => {
  return {
    '--assistant-color': props.assistant.avatar_bg_color || 'var(--q-accent)',
  };
});

const glowStyle = computed(() => {
  const color = providerColor.value || 'grey-7';
  return {
    background: `radial-gradient(circle at 50% 0%, var(--q-${color})15 0%, transparent 70%)`,
  };
});
</script>

<style scoped>
.assistant-selection-card {
  background: var(--q-primary);
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.assistant-card-banner {
  height: 80px;
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.glow-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  pointer-events: none;
  opacity: 0.6;
  transition: opacity 0.4s ease;
}

.assistant-selection-card:hover {
  transform: translateY(-8px);
  border-color: var(--q-sixth);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.assistant-selection-card:hover .glow-overlay {
  opacity: 0.8;
}

.avatar-wrapper {
  margin-top: -40px;
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}

.avatar-ring {
  padding: 4px;
  border: 4px solid;
  border-radius: 50%;
  transition: all 0.4s ease;
  background: var(--q-primary);
}

.assistant-selection-card:hover .avatar-ring {
  transform: scale(1.05) rotate(2deg);
}

.header-badges-vertical {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  z-index: 5;
}

.assistant-name {
  letter-spacing: -0.01em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  line-height: 1.1;
}

.model-pill {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.provider-logo {
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2));
}

.description-text {
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--q-text-sub);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  opacity: 0.5;
  min-height: 38px;
}

.tag-badge {
  background-color: var(--q-sixth);
  border: 1px solid var(--q-third);
  color: var(--q-text-sub);
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.9;
}

.tag-badge.more {
  border-style: dashed;
}

.action-btn-styled {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 12px;
  font-weight: 700;
  transition: all 0.3s ease;
  letter-spacing: 0.02em;
}

.assistant-selection-card:hover .action-btn-styled {
  color: var(--assistant-color);
}
</style>
