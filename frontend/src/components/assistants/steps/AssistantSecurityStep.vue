<template>
  <div class="row justify-center">
    <div class="col-10">
      <div class="row items-center justify-between q-pa-md bg-secondary rounded-borders">
        <div>
          <div class="text-subtitle1 text-weight-medium">{{ $t('userAuthentication') }}</div>
          <div class="text-caption text-grey-7">{{ $t('userAuthenticationHint') }}</div>
        </div>
        <q-toggle v-model="localData.user_authentication" color="accent" size="lg" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Assistant } from 'src/services/assistantService';

defineOptions({
  name: 'AssistantSecurityStep',
});

const props = defineProps<{
  modelValue: Partial<Assistant>;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', val: Partial<Assistant>): void;
}>();

const localData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});
</script>

<style scoped>
.rounded-borders {
  border-radius: 12px;
  border: 1px solid var(--q-sixth);
}
</style>
