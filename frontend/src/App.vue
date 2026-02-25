<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useTheme } from 'src/composables/useTheme';
import { settingsService } from 'src/services/settingsService';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { useAuthStore } from 'src/stores/authStore';

const { initTheme } = useTheme();
const { locale } = useI18n();
const $q = useQuasar();
const authStore = useAuthStore();

onMounted(async () => {
  void initTheme();

  // Only sync settings if we are authenticated, otherwise we rely on localdefaults/login
  if (authStore.isAuthenticated) {
    await syncGlobalSettings();
  }
});

async function syncGlobalSettings() {
  try {
    const settings = await settingsService.getAll();
    const languageSetting = settings.find((s) => s.key === 'app_language');

    if (languageSetting && languageSetting.value) {
      const lang = languageSetting.value;

      // If DB language differs from current runtime (init from localStorage), sync it
      if (locale.value !== lang) {
        console.log('[App] Syncing language from DB:', lang);
        locale.value = lang;
        localStorage.setItem('app_language', lang);

        try {
          // Static import map for Vite analysis
          let qLang;
          if (lang === 'fr') {
            qLang = await import('quasar/lang/fr');
          } else {
            // Default to en-US
            qLang = await import('quasar/lang/en-US');
          }

          if (qLang) {
            $q.lang.set(qLang.default);
          }
        } catch (e) {
          console.warn('[App] Could not load Quasar lang pack:', e);
        }
      }
    }
  } catch (e) {
    // Silent fail - maybe API is down or not auth
    console.debug('[App] Settings sync skipped or failed', e);
  }
}
</script>
