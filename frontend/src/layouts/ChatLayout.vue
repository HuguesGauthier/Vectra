<template>
  <q-layout view="hHh Lpr fFf" class="bg-dark-page">
    <!-- Clean Header -->
    <q-header class="bg-dark-page text-white" style="border-bottom: 1px solid #333">
      <q-toolbar>
        <q-toolbar-title class="row items-center">
          <div id="chat-header-portal"></div>
        </q-toolbar-title>

        <!-- Language Switcher -->
        <q-btn-dropdown
          flat
          dense
          icon="language"
          class="q-mr-sm"
          :color="store.currentAssistantColor"
        >
          <q-list>
            <q-item clickable v-close-popup @click="setLanguage('en-US')">
              <q-item-section>{{ $t('langEnglish') }}</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="setLanguage('fr')">
              <q-item-section>{{ $t('langFrench') }}</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { usePublicChatStore } from 'src/stores/publicChatStore';
import { settingsService } from 'src/services/settingsService';

// --- DEFINITIONS ---
defineOptions({
  name: 'ChatLayout',
});

// --- STATE ---
const { locale } = useI18n();
const store = usePublicChatStore();

/**
 * Updates the application language and persists the choice to the backend.
 * @param {string} lang - The language code (e.g. 'en-US', 'fr')
 */
async function setLanguage(lang: string) {
  locale.value = lang;
  try {
    await settingsService.updateBatch([
      { key: 'app_language', value: lang, group: 'general', is_secret: false },
    ]);
  } catch (err) {
    console.error('Failed to persist language preference', err);
  }
}
</script>

<style scoped>
.bg-dark-page {
  background-color: #121212;
}

.bg-dark-drawer {
  background-color: #1e1e1e;
}

.bg-dark-card {
  background-color: #252525;
  border-radius: 12px;
}

.bg-dark-lighter {
  background-color: #2c2c2c;
}

.border-dark {
  border: 1px solid #333;
}
</style>
