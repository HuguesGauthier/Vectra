<template>
  <q-layout view="lHh LpR lFf" class="bg-primary">
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
defineOptions({
  name: 'StandaloneLayout',
});
</script>

<style scoped>
/* Ensure the layout takes full height for embedded content */
.q-layout {
  min-height: 100vh !important;
}
</style>
