<template>
  <q-page class="column justify-between items-center overflow-hidden">
    <!-- Spacer for centering -->
    <div class="col-auto"></div>

    <!-- Hero / Branding -->
    <div class="column items-center relative-position z-10">
      <div class="logo-container q-mb-none">
        <VectraLogo
          :color-left="currentColors.left"
          :color-right="currentColors.right"
          :color-mid="currentColors.mid"
          style="width: 300px; height: 300px"
          class="q-mb-md"
        />
      </div>
      <div class="text-h1 text-weight-bold brand-font q-mb-sm tracking-tight">Vectra</div>

      <!-- Slogan with fade-in -->
      <div class="row q-gutter-x-md text-h4 text-weight-light slogan-container text-grey-5">
        <span class="fade-in-1">{{ t('sloganConnect') }}</span>
        <span class="fade-in-2">{{ t('sloganVectorize') }}</span>
        <span class="fade-in-3">{{ t('sloganChat') }}</span>
      </div>
    </div>

    <!-- Footer -->
    <div class="column items-center q-mb-lg z-10">
      <div
        class="row items-center q-gutter-x-sm text-uppercase tracking-widest text-caption text-grey-6"
      >
        <span class="text-weight-medium">RAG MANAGEMENT SYSTEM</span>
        <span>v{{ version }}</span>
      </div>
      <a
        href="https://huguesgauthier.com"
        target="_blank"
        class="text-caption text-grey-5 q-mt-xs tracking-wide footer-link"
      >
        huguesgauthier.com
      </a>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { version } from '../../package.json';
import VectraLogo from 'src/components/home/VectraLogo.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'HomePage',
});

// --- STATE ---
const { t } = useI18n();

// État réactif pour stocker les couleurs actuelles du logo
// Initialisé avec les couleurs par défaut
const currentColors = reactive({
  left: '#2A4B7C',
  right: '#b08989',
  mid: '#7D6868',
});
</script>

<style scoped lang="scss">
.bg-dark-page {
  background: radial-gradient(circle at top, var(--q-primary) 80%, var(--q-secondary) 100%);
}

.bg-dark-card {
  background: var(--q-fourth);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hover-effect:hover {
  transform: translateY(-8px);
  background: rgba(40, 40, 40, 0.8);
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.5);
}

.hover-effect:hover .text-gradient-1 {
  color: var(--q-accent);
  filter: drop-shadow(0 0 8px rgba(79, 172, 254, 0.6));
}

.hover-effect:hover .text-gradient-2 {
  color: var(--q-accent);
  filter: drop-shadow(0 0 8px rgba(255, 154, 158, 0.6));
}

.hover-effect:hover .text-gradient-3 {
  color: var(--q-accent);
  filter: drop-shadow(0 0 8px rgba(161, 140, 209, 0.6));
}

.text-gradient-1,
.text-gradient-2,
.text-gradient-3 {
  transition: all 0.3s ease;
  color: #e0e0e0;
}

.shadow-20 {
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.5);
}

.glow-effect img {
  filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.1));
}

.tracking-tight {
  letter-spacing: -2px;
}

.tracking-widest {
  letter-spacing: 0.3em;
}

/* Animations */
.fade-in-1,
.fade-in-2,
.fade-in-3 {
  opacity: 0;
  animation: fadeIn 1.2s ease-out forwards;
}

.fade-in-1 {
  animation-delay: 0.2s;
}
.fade-in-2 {
  animation-delay: 0.8s;
}
.fade-in-3 {
  animation-delay: 1.4s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.icon-wrapper {
  padding: 1rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.03);
  transition: all 0.3s ease;
}

.hover-effect:hover .icon-wrapper {
  background: rgba(255, 255, 255, 0.08);
}

.footer-link {
  text-decoration: none;
  transition: all 0.3s ease;

  &:hover {
    color: var(--q-primary) !important;
  }
}
</style>
