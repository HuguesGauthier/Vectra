<template>
  <transition name="fade-slide">
    <div v-if="currentStep" class="pipeline-step-indicator" :class="`status-${currentStep.status}`">
      <div class="row items-center q-gutter-x-sm no-wrap">
        <!-- Animated Icon -->
        <q-spinner-dots v-if="currentStep.status === 'running'" size="14px" color="warning" />
        <q-icon
          v-else-if="currentStep.status === 'completed'"
          name="check_circle"
          size="14px"
          color="positive"
        />
        <q-icon v-else name="error" size="14px" color="negative" />

        <!-- Step Label -->
        <span class="text-caption text-weight-medium ellipsis">
          {{ currentStep.label }}
        </span>

        <!-- Duration Badge (only when completed) -->
        <q-badge
          v-if="currentStep.duration"
          color="transparent"
          text-color="white"
          class="text-caption"
          style="opacity: 0.7"
        >
          {{ currentStep.duration.toFixed(1) }}s
        </q-badge>

        <!-- Token Badge (only when completed with tokens) -->
        <q-badge
          v-if="
            currentStep.tokens && (currentStep.tokens.input > 0 || currentStep.tokens.output > 0)
          "
          color="transparent"
          text-color="white"
          class="text-caption"
          style="opacity: 0.7"
        >
          <span class="q-mr-xs">↑</span>{{ currentStep.tokens.input || 0 }}
          <span class="q-mx-xs">|</span> <span class="q-mr-xs">↓</span
          >{{ currentStep.tokens.output || 0 }}
        </q-badge>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { type ChatStep } from 'src/modules/chat/composables/useChatStream';

const props = defineProps<{
  steps?: ChatStep[];
}>();

// Show only the LAST step (current one)
const currentStep = computed(() => {
  if (!props.steps || props.steps.length === 0) return null;
  // Return the last step that is either running or just completed
  const lastStep = props.steps[props.steps.length - 1];
  // Only show if not the final "completed" step
  if (lastStep?.step_type === 'completed' && lastStep?.status === 'completed') {
    return null;
  }
  return lastStep;
});
</script>

<style scoped>
.pipeline-step-indicator {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: inline-flex;
  align-items: center;
  max-width: 400px;
  backdrop-filter: blur(10px);
  margin-bottom: 12px;
  font-size: 12px;
}

.pipeline-step-indicator.status-running {
  border-color: rgba(251, 192, 45, 0.3);
  background: rgba(251, 192, 45, 0.1);
}

.pipeline-step-indicator.status-completed {
  border-color: rgba(33, 186, 69, 0.3);
  background: rgba(33, 186, 69, 0.1);
}

.pipeline-step-indicator.status-failed {
  border-color: rgba(244, 67, 54, 0.3);
  background: rgba(244, 67, 54, 0.1);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
