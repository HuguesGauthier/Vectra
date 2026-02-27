<template>
  <div class="animated-gradient-bg"></div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'AnimatedGradientBackground',
});
</script>

<style scoped>
.animated-gradient-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  background: linear-gradient(
    -45deg,
    var(--q-primary),
    var(--q-secondary),
    var(--q-primary),
    var(--q-secondary)
  );
  background-size: 400% 400%;
  animation: gradientAnimation 15s ease infinite;
}

@keyframes gradientAnimation {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* Light mode overrides if needed, but primary/secondary usually adapt */
body.body--light .animated-gradient-bg {
  opacity: 0.8;
}
</style>
