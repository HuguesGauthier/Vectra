<template>
  <q-card
    flat
    class="ai-provider-card full-height column justify-between"
    :class="{
      selected: selectable && selected,
      disabled: disabled && !selected,
      selectable: selectable,
      compact: compact,
      clickable: (selectable || showConfig) && !disabled,
      'q-pa-md': !compact,
      'q-pa-sm': compact,
    }"
    v-ripple="(selectable || showConfig) && !disabled"
    @click="handleClick"
  >
    <!-- Selected Icon Overlay -->
    <div v-if="selectable && selected" class="selected-overlay">
      <q-icon name="check_circle" color="accent" size="24px" />
    </div>

    <!-- Main Content -->
    <q-card-section
      class="col-grow column items-center text-center no-wrap"
      :class="compact ? 'q-pt-xs' : 'q-pt-md'"
    >
      <!-- Logo Container -->
      <div
        class="logo-container q-mb-sm relative-position"
        :class="{ 'grayscale-filter': disabled && !selected }"
      >
        <img
          :src="logo"
          :style="{
            width: compact ? '40px' : '56px',
            height: compact ? '40px' : '56px',
            objectFit: 'contain',
          }"
        />

        <!-- Badge (Private/Public) -->
        <q-badge
          v-if="badge"
          floating
          :color="badgeColor || 'primary'"
          rounded
          class="provider-badge"
          :style="{ top: compact ? '-5px' : '-8px', right: compact ? '-10px' : '-15px' }"
        >
          {{ badge }}
        </q-badge>
      </div>

      <!-- Title & Tagline -->
      <div
        class="text-weight-bold text-main"
        :class="compact ? 'text-subtitle2' : 'text-subtitle1'"
        style="line-height: 1.2"
      >
        {{ label }}
      </div>

      <div
        v-if="tagline"
        class="text-caption text-sub q-mt-xs text-italic opacity-80"
        style="font-size: 0.7rem"
      >
        {{ tagline }}
      </div>

      <!-- Model Info (Critical Config) -->
      <div
        v-if="modelInfo"
        class="text-caption text-accent q-mt-xs text-weight-medium"
        style="font-size: 0.75rem"
      >
        {{ modelInfo }}
      </div>

      <!-- Description (Full mode only) -->
      <div
        v-if="description && !compact"
        class="text-caption text-grey-7 q-mt-md line-clamp-3"
        style="line-height: 1.3; font-size: 0.75rem"
      >
        {{ description }}
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
/**
 * AiProviderCard.vue
 * A premium, reusable card for displaying an AI Provider.
 * Centralizes design, hover effects, and states.
 */

defineOptions({
  name: 'AiProviderCard',
});

defineProps<{
  label?: string | undefined;
  logo?: string | undefined;
  tagline?: string | undefined;
  description?: string | undefined;
  badge?: string | undefined;
  badgeColor?: string | undefined;
  selected?: boolean | undefined;
  selectable?: boolean | undefined;
  disabled?: boolean | undefined;
  compact?: boolean | undefined;
  showConfig?: boolean | undefined;
  modelInfo?: string | undefined;
}>();

const emit = defineEmits<{
  (e: 'click'): void;
  (e: 'configure'): void;
}>();

function handleClick() {
  emit('click');
}
</script>

<style scoped>
.ai-provider-card {
  background: var(--q-secondary);
  border: 1px solid var(--q-third);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  min-height: 140px;
  max-width: 350px;
}

.ai-provider-card.compact {
  min-height: 100px;
}

.ai-provider-card.selectable {
  cursor: pointer;
}

.ai-provider-card.clickable:hover {
  border-color: var(--q-accent);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.ai-provider-card.selected {
  border-color: var(--q-accent);
  background: rgba(var(--q-accent-rgb), 0.05);
  box-shadow: 0 0 0 2px var(--q-accent);
}

.ai-provider-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-style: dashed;
}

.selected-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  animation: scale-in 0.2s ease-out;
}

.logo-container {
  transition: transform 0.3s ease;
}

.ai-provider-card:hover .logo-container:not(.grayscale-filter) {
  transform: scale(1.1);
}

.grayscale-filter {
  filter: grayscale(100%);
  opacity: 0.4;
}

.provider-badge {
  font-size: 0.6rem;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.text-main {
  color: var(--q-text-main);
}

.text-sub {
  color: var(--q-text-sub);
}

.opacity-80 {
  opacity: 0.8;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@keyframes scale-in {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
