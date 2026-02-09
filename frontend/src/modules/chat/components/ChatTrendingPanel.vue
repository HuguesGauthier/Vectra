<template>
  <transition name="slide-right">
    <div
      v-if="isOpen"
      class="column q-pa-md"
      style="
        width: 320px;
        min-width: 320px;
        border-left: 1px solid var(--q-third);
        overflow-y: auto;
      "
    >
      <div class="text-h6 q-mb-md flex items-center justify-center">
        {{ $t('trendingQuestions') || 'Hot Topics' }}
      </div>

      <TrendingList
        v-if="assistantId"
        :assistant-id="assistantId"
        :interactive="true"
        @select="onSelect"
      />
    </div>
  </transition>
</template>

<script setup lang="ts">
import TrendingList from 'src/components/common/TrendingList.vue';

defineProps<{
  isOpen: boolean;
  assistantId?: string;
}>();

const emit = defineEmits<{
  (e: 'select', text: string): void;
}>();

function onSelect(text: string) {
  emit('select', text);
}
</script>

<style scoped>
/* Ensure transition works */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
  width: 0 !important;
  min-width: 0 !important;
  padding: 0 !important;
}
</style>
