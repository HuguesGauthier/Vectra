<template>
  <q-card
    flat
    class="assistant-management-card bg-primary column full-height clickable"
    @click="$emit('edit')"
  >
    <div class="assistant-card-banner">
      <div class="glow-overlay" :style="glowStyle"></div>

      <!-- Top Right Header Badges & Actions -->
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

        <!-- Actions Menu -->
        <q-btn
          round
          flat
          dense
          icon="more_vert"
          color="white"
          class="glass-btn q-mt-xs"
          @click.stop
        >
          <q-menu auto-close class="bg-primary text-white border-sixth">
            <q-list style="min-width: 150px">
              <q-item clickable @click.stop="$emit('chat')">
                <q-item-section avatar>
                  <q-icon name="chat_bubble_outline" size="xs" />
                </q-item-section>
                <q-item-section>{{ $t('talk') }}</q-item-section>
              </q-item>
              <q-item clickable @click.stop="$emit('share')">
                <q-item-section avatar>
                  <q-icon name="share" size="xs" />
                </q-item-section>
                <q-item-section>{{ $t('share') }}</q-item-section>
              </q-item>
              <q-separator dark />
              <q-item clickable class="text-warning" @click.stop="$emit('purge')">
                <q-item-section avatar>
                  <q-icon name="delete_sweep" size="xs" color="warning" />
                </q-item-section>
                <q-item-section>{{ $t('performance.purgeCache') }}</q-item-section>
              </q-item>
              <q-item clickable class="text-negative" @click.stop="$emit('delete')">
                <q-item-section avatar>
                  <q-icon name="delete" size="xs" color="negative" />
                </q-item-section>
                <q-item-section>{{ $t('delete') }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </div>
    </div>

    <q-card-section
      class="q-pt-none q-px-lg relative-position info-section col cursor-pointer"
      v-ripple
    >
      <!-- Overlapping Avatar -->
      <div class="avatar-wrapper">
        <div
          class="avatar-ring"
          :style="{ borderColor: assistant.avatar_bg_color || 'var(--q-accent)' }"
        >
          <AssistantAvatar
            :assistant="assistant"
            size="80px"
            class="assistant-avatar-main shadow-5"
            :refreshKey="refreshKey"
          />
        </div>
      </div>

      <!-- Assistant Info -->
      <div class="column q-mt-sm">
        <div class="text-h6 text-weight-bolder assistant-name q-mb-xs ellipsis">
          {{ assistant.name }}
        </div>

        <div class="description-text q-mb-md">
          {{ assistant.description || '...' }}
          <AppTooltip v-if="assistant.description && assistant.description.length > 60">
            {{ assistant.description }}
          </AppTooltip>
        </div>

        <!-- Data Sources Section -->
        <div class="section-label q-mb-xs">{{ $t('dataSources') }}</div>
        <div class="row q-gutter-xs q-mb-md min-h-24">
          <template v-if="connectors.length > 0">
            <q-badge v-for="source in connectors.slice(0, 2)" :key="source.id" class="source-badge">
              {{ source.name }}
            </q-badge>
            <q-badge v-if="connectors.length > 2" class="source-badge more">
              +{{ connectors.length - 2 }}
            </q-badge>
          </template>
          <div v-else class="text-caption text-grey-7">—</div>
        </div>

        <!-- ACL / Tags Section -->
        <div class="section-label q-mb-xs">{{ $t('acl') }}</div>
        <div class="row q-gutter-xs min-h-24">
          <template v-if="tags.length > 0">
            <q-badge v-for="tag in tags.slice(0, 3)" :key="tag" class="tag-badge">
              {{ tag }}
            </q-badge>
            <q-badge v-if="tags.length > 3" class="tag-badge more">
              +{{ tags.length - 3 }}
            </q-badge>
          </template>
          <div v-else class="text-caption text-grey-7">—</div>
        </div>
      </div>
    </q-card-section>

    <!-- Quick Actions Footer -->
    <q-card-actions align="around" class="assistant-card-footer q-pb-md q-px-md">
      <q-btn
        flat
        round
        dense
        icon="chat_bubble_outline"
        size="sm"
        class="action-btn"
        @click.stop="$emit('chat')"
      >
        <AppTooltip>{{ $t('talk') }}</AppTooltip>
      </q-btn>
      <q-btn
        flat
        round
        dense
        icon="share"
        size="sm"
        class="action-btn"
        @click.stop="$emit('share')"
      >
        <AppTooltip>{{ $t('share') }}</AppTooltip>
      </q-btn>
    </q-card-actions>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AssistantAvatar from 'src/components/assistants/AssistantAvatar.vue';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import type { Assistant } from 'src/services/assistantService';
import { useAiProviders } from 'src/composables/useAiProviders';

const props = defineProps<{
  assistant: Assistant;
  connectors: { id: string; name: string }[];
  refreshKey: number;
}>();

defineEmits(['edit', 'delete', 'share', 'chat', 'purge']);

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
    backdropFilter: 'blur(8px)',
    border: `1px solid rgba(var(--q-${color}-rgb, 100, 100, 100), 0.25)`,
    color: `var(--q-${color})`,
  };
});

const glowStyle = computed(() => {
  const color = providerColor.value || 'grey-7';
  return {
    background: `radial-gradient(circle at 50% 0%, var(--q-${color})20 0%, transparent 70%)`,
  };
});
</script>

<style scoped>
.assistant-management-card {
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.assistant-management-card:hover {
  transform: translateY(-8px);
  border-color: var(--q-sixth);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.assistant-card-banner {
  height: 80px;
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.assistant-card-footer {
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
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

.assistant-management-card:hover .glow-overlay {
  opacity: 0.8;
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

.model-pill {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.glass-btn {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.avatar-wrapper {
  margin-top: -40px;
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
  z-index: 2;
}

.avatar-ring {
  padding: 4px;
  border: 4px solid;
  border-radius: 50%;
  transition: all 0.4s ease;
  background: var(--q-primary);
}

.assistant-management-card:hover .avatar-ring {
  transform: scale(1.05) rotate(2deg);
}

.assistant-name {
  letter-spacing: -0.01em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  line-height: 1.1;
  transition: color 0.3s ease;
}

.hover-accent:hover {
  color: var(--q-accent);
}

.description-text {
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--q-text-sub);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  opacity: 0.6;
  min-height: 2.3em;
}

.section-label {
  font-size: 0.6rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--q-text-sub);
  opacity: 0.4;
}

.min-h-24 {
  min-height: 24px;
}

.source-badge {
  background-color: rgba(var(--q-accent-rgb), 0.1);
  border: 1px solid rgba(var(--q-accent-rgb), 0.2);
  color: var(--q-accent);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.65rem;
  font-weight: 600;
}

.tag-badge {
  background-color: var(--q-sixth);
  border: 1px solid var(--q-third);
  color: var(--q-text-sub);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.65rem;
  font-weight: 600;
}

.source-badge.more,
.tag-badge.more {
  border-style: dashed;
  opacity: 0.6;
}

.action-btn {
  color: var(--q-text-sub);
  opacity: 0.5;
  transition: all 0.3s ease;
}

.action-btn:hover {
  opacity: 1;
  color: var(--q-accent);
  transform: scale(1.1);
}

.border-sixth {
  border: 1px solid var(--q-sixth);
}
</style>
