<template>
  <q-page
    class="column bg-primary items-center no-wrap window-height"
    style="max-height: 90vh; overflow: hidden"
  >
    <slot name="header"></slot>

    <!-- Main Content -->
    <div
      class="col column relative-position chat-container q-ma-md no-wrap"
      style="background-color: var(--q-fourth); min-height: 0"
    >
      <slot name="trending-toggle"></slot>

      <!-- Main Chat Area with Sliding Panel -->
      <div class="row no-wrap" style="height: 100%; background-color: var(--q-fourth)">
        <!-- Chat Content -->
        <div
          class="no-wrap"
          :style="{
            minHeight: 0,
            flex: rightDrawerOpen ? '1 1 auto' : '1',
            transition: 'all 0.3s ease',
            maxWidth: rightDrawerOpen ? 'calc(100% - 320px)' : '100%',
            display: 'flex',
            flexDirection: 'column',
          }"
        >
          <!-- Header Spacer -->
          <div style="height: 50px; min-height: 50px; flex-shrink: 0"></div>

          <div class="col column no-wrap relative-position" style="min-height: 0">
            <slot name="messages"></slot>
          </div>

          <slot name="input"></slot>
        </div>

        <slot name="trending-panel"></slot>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
defineProps<{
  rightDrawerOpen: boolean;
}>();
</script>

<style scoped>
.chat-container {
  width: 50vw;
  min-width: 350px;
  border-radius: 24px;
  overflow: hidden;
  background: linear-gradient(
    145deg,
    var(--q-secondary) 0%,
    rgba(var(--q-secondary-rgb), 0.9) 100%
  ) !important;
  border: 1px solid var(--q-third);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

:deep(.bg-primary) {
  background: radial-gradient(circle at 50% 0%, var(--q-secondary) 0%, var(--q-primary) 100%) !important;
}
</style>
