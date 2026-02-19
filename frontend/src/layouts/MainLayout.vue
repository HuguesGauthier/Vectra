<template>
  <div class="column window-height window-width overflow-hidden">
    <CustomTitleBar />
    <q-layout view="lHh LpR lFf" container class="col">
      <q-header class="bg-secondary" style="color: var(--q-icon-color)">
        <!-- Storage Warning Banner -->
        <q-banner
          v-if="socketStore.storageStatus === 'offline' && authStore.isAdmin"
          dense
          inline-actions
          class="bg-orange-9 text-white q-py-xs"
        >
          <template v-slot:avatar>
            <q-icon name="storage" />
          </template>
          <div class="row items-center">
            <span class="text-weight-bold q-mr-sm">🚨 {{ $t('storageOfflineTitle') }}</span>
            <span class="text-caption text-italic">
              {{ $t('storageOfflineDesc') }}
            </span>
          </div>
          <template v-slot:action>
            <q-btn flat color="white" label="FIX" @click="showFixStorageDialog = true" />
          </template>
        </q-banner>

        <q-toolbar style="border-bottom: 1px solid var(--q-third); position: relative">
          <!-- Back Button for Connector Documents -->
          <q-btn
            v-if="route.name === 'ConnectorDocuments'"
            round
            color="accent"
            dense
            icon="arrow_back"
            class="q-mr-sm"
            @click="router.push({ name: 'Connectors' })"
          >
            <AppTooltip>{{ $t('back') }}</AppTooltip>
          </q-btn>

          <q-space />

          <q-btn-dropdown dark flat dense icon="language" class="q-mr-sm">
            <q-list>
              <q-item clickable v-close-popup @click="setLanguage('en-US')">
                <q-item-section>{{ $t('langEnglish') }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="setLanguage('fr')">
                <q-item-section>{{ $t('langFrench') }}</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>

          <!-- Theme Toggle -->
          <q-btn flat dense round :icon="themeIcon" class="q-mr-sm" @click="toggleTheme">
            <AppTooltip>{{ $t('theme') }}</AppTooltip>
          </q-btn>

          <div class="q-gutter-sm row items-center no-wrap">
            <!-- Notification Bell -->
            <q-btn
              flat
              round
              dense
              icon="notifications"
              @click="toggleRightDrawer('notifications')"
            >
              <q-badge color="red" floating v-if="notificationStore.unreadCount > 0">
                {{ notificationStore.unreadCount }}
              </q-badge>
              <AppTooltip>{{ $t('notifications') }}</AppTooltip>
            </q-btn>

            <!-- Debug Button -->
            <q-btn flat round dense icon="bug_report" @click="toggleRightDrawer('debug')">
              <AppTooltip>{{ $t('debug') }}</AppTooltip>
            </q-btn>
          </div>

          <!-- Chat Header Portal Target - Absolutely Positioned Center -->
          <div id="chat-header-portal" class="chat-header-portal"></div>
        </q-toolbar>
      </q-header>

      <q-drawer
        v-model="leftDrawerOpen"
        show-if-above
        :width="300"
        class="bg-secondary"
        style="border-right: 1px solid var(--q-third)"
      >
        <div class="column full-height">
          <q-list class="col" padding>
            <q-item class="q-ma-none q-pa-sm" clickable :to="isHomePage ? undefined : '/'">
              <q-item-section avatar>
                <VectraLogo
                  :color-left="currentColors.left"
                  :color-right="currentColors.right"
                  :color-mid="currentColors.mid"
                  :disable-animation="true"
                  :small="true"
                  style="width: 36px; height: 36px"
                />
              </q-item-section>
              <q-item-section>
                <span class="vectra-brand-name">Vectra</span>
              </q-item-section>
            </q-item>

            <!-- Admin Menu Items -->
            <template v-if="authStore.isAdmin">
              <q-separator class="q-my-sm" style="background-color: var(--q-third)" />

              <q-item
                clickable
                to="/admin/dashboard"
                active-class="active-menu-item"
                class="menu-item"
              >
                <q-item-section avatar>
                  <q-icon name="dashboard" />
                </q-item-section>
                <q-item-section>
                  {{ $t('dashboard') }}
                </q-item-section>
              </q-item>

              <q-item
                clickable
                to="/admin/analytics"
                active-class="active-menu-item"
                class="menu-item"
              >
                <q-item-section avatar>
                  <q-icon name="analytics" />
                </q-item-section>
                <q-item-section>
                  {{ $t('analytics') }}
                </q-item-section>
              </q-item>

              <q-item
                clickable
                to="/admin/connectors"
                active-class="active-menu-item text-white"
                class="menu-item"
              >
                <q-item-section avatar>
                  <q-icon name="hub" />
                </q-item-section>
                <q-item-section>
                  {{ $t('knowledgeBase') }}
                </q-item-section>
              </q-item>

              <q-item
                clickable
                to="/admin/assistants"
                active-class="active-menu-item text-white"
                class="menu-item"
              >
                <q-item-section avatar>
                  <q-icon name="psychology" />
                </q-item-section>
                <q-item-section>
                  {{ $t('myAssistants') }}
                </q-item-section>
              </q-item>
            </template>

            <!-- Chat (Public) -->
            <q-item
              clickable
              to="/chat"
              active-class="active-menu-item text-white"
              class="menu-item"
            >
              <q-item-section avatar>
                <q-icon name="chat_bubble_outline" />
              </q-item-section>
              <q-item-section>
                {{ $t('chat') }}
              </q-item-section>
            </q-item>
          </q-list>

          <template v-if="authStore.isAdmin">
            <q-separator class="q-my-md" style="background-color: var(--q-third)" />
            <q-item
              clickable
              to="/admin/users"
              active-class="active-menu-item text-white"
              class="menu-item"
            >
              <q-item-section avatar>
                <q-icon name="people" />
              </q-item-section>
              <q-item-section>
                {{ $t('users') }}
              </q-item-section>
            </q-item>
          </template>

          <template v-else>
            <q-separator
              class="q-my-md"
              style="background-color: var(--q-third)"
              v-if="authStore.isAuthenticated"
            />
          </template>

          <!-- User Profile Bar -->
          <div class="user-profile-bar row items-center q-pa-sm q-ma-sm">
            <q-avatar
              size="32px"
              class="q-mr-sm relative-position"
              :color="authStore.user?.avatar_url ? 'transparent' : 'grey'"
            >
              <template v-if="authStore.user?.avatar_url">
                <img
                  :src="`http://localhost:8000/api/v1${authStore.user.avatar_url}`"
                  :style="{
                    objectFit: 'cover',
                    objectPosition: `center ${authStore.user.avatar_vertical_position || 50}%`,
                  }"
                />
              </template>
              <template v-else>
                <q-icon v-if="authStore.isAdmin" name="admin_panel_settings" size="20px" />
                <q-icon v-else name="account_circle" size="32px" color="white" />
              </template>
              <div v-if="authStore.isAuthenticated" class="status-badge bg-positive"></div>
              <!-- Storage Health Dot (Admins Only) -->
              <div
                v-if="authStore.isAdmin && socketStore.storageStatus === 'offline'"
                class="storage-badge bg-negative"
              >
                <q-tooltip> {{ $t('storage') }}: {{ $t('statusOffline') }} </q-tooltip>
              </div>
            </q-avatar>
            <div class="column col">
              <div class="text-white text-weight-bold text-caption ellipsis">
                {{
                  authStore.user?.first_name || authStore.user?.last_name
                    ? `${authStore.user?.first_name || ''} ${authStore.user?.last_name || ''}`.trim()
                    : authStore.user?.email ||
                      (authStore.isAuthenticated ? $t('roleAdmin') : $t('roleGuest'))
                }}
              </div>
              <div class="text-caption text-grey-5" style="font-size: 11px">
                {{ authStore.isAuthenticated ? $t('statusOnline') : $t('statusAnonymous') }}
              </div>
            </div>

            <div class="row">
              <template v-if="authStore.isAuthenticated">
                <q-btn
                  flat
                  round
                  dense
                  icon="settings"
                  size="sm"
                  class="hover-white"
                  to="/admin/settings"
                />
                <q-btn flat round dense icon="logout" size="sm" class="hover-white" @click="logout">
                  <AppTooltip>{{ $t('logout') }}</AppTooltip>
                </q-btn>
              </template>
              <template v-else>
                <q-btn flat round dense icon="login" size="sm" class="bg-primary" to="/login">
                  <AppTooltip>{{ $t('login') }}</AppTooltip>
                </q-btn>
              </template>
            </div>
          </div>
        </div>
      </q-drawer>

      <!-- Right Drawer for Notifications & Debug -->
      <q-drawer
        v-model="rightDrawerOpen"
        side="right"
        behavior="desktop"
        style="border-left: 1px solid var(--q-third); color: var(--q-text-main)"
        :width="350"
      >
        <div class="column full-height bg-secondary">
          <!-- Drawer Header with Tabs -->
          <div class="row items-center justify-between q-pa-sm border-bottom">
            <q-tabs
              v-model="rightDrawerTab"
              dense
              active-color="accent"
              indicator-color="accent"
              align="left"
              narrow-indicator
            >
              <q-tab name="notifications" icon="notifications" />
              <q-tab name="debug" icon="bug_report" />
            </q-tabs>
            <q-btn flat round dense icon="close" size="sm" @click="rightDrawerOpen = false" />
          </div>

          <!-- Content -->
          <q-tab-panels v-model="rightDrawerTab" animated class="col bg-transparent">
            <!-- Notifications Panel -->
            <q-tab-panel name="notifications" class="q-pa-none column full-height">
              <q-toolbar class="border-bottom q-min-height-none q-py-xs">
                <q-space />
                <div class="row q-gutter-x-xs">
                  <q-btn
                    flat
                    dense
                    round
                    icon="done_all"
                    size="sm"
                    :title="$t('readAll')"
                    @click="notificationStore.markAllRead()"
                    v-if="notificationStore.unreadCount > 0"
                  />
                  <q-btn
                    flat
                    dense
                    round
                    icon="delete_sweep"
                    size="sm"
                    :title="$t('clearAll')"
                    @click="notificationStore.clearAll()"
                    v-if="notificationStore.notifications.length > 0"
                  />
                </div>
              </q-toolbar>
              <q-scroll-area class="col">
                <NotificationList />
              </q-scroll-area>
            </q-tab-panel>

            <!-- Debug Panel -->
            <q-tab-panel name="debug" class="q-pa-none column full-height">
              <DebugPanel />
            </q-tab-panel>
          </q-tab-panels>
        </div>
      </q-drawer>

      <q-page-container class="bg-primary column">
        <router-view />
      </q-page-container>

      <!-- Storage Fix Dialog -->
      <q-dialog v-model="showFixStorageDialog">
        <q-card style="min-width: 400px; background: var(--q-secondary); color: white">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ $t('storageFixTitle') }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>

          <q-card-section class="q-pa-md">
            <div class="column q-gutter-md">
              <div class="text-subtitle2">{{ $t('storageFixPathLabel') }}</div>
              <code class="bg-black q-pa-sm borderRadius-8" style="font-family: monospace">
                d:\Vectra\.env
              </code>

              <div class="text-body2 q-mt-md">
                <div class="q-mb-xs">{{ $t('storageFixStep1') }}</div>
                <div class="q-mb-xs">{{ $t('storageFixStep2') }}</div>
                <div class="q-mb-xs">{{ $t('storageFixStep3') }}</div>
                <div class="q-mb-xs">{{ $t('storageFixStep4') }}</div>
              </div>

              <q-banner dense class="bg-grey-9 text-grey-4 text-caption borderRadius-4 q-mt-sm">
                <template v-slot:avatar>
                  <q-icon name="info" size="xs" />
                </template>
                docker compose --profile app up -d --build
              </q-banner>
            </div>
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat label="OK" color="primary" v-close-popup />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </q-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useNotificationStore } from 'src/stores/notificationStore';
import { useNotification } from 'src/composables/useNotification';
import { useAuthStore } from 'src/stores/authStore';
import { useSocketStore } from 'src/stores/socketStore';
import { useConnectorStore } from 'src/stores/ConnectorStore';
import { useTheme } from 'src/composables/useTheme';
import { settingsService } from 'src/services/settingsService';
import { useRouter, useRoute } from 'vue-router';
import NotificationList from 'src/components/notifications/NotificationList.vue';
import CustomTitleBar from 'src/components/layout/CustomTitleBar.vue';
import AppTooltip from 'src/components/common/AppTooltip.vue';
import DebugPanel from 'src/components/debug/DebugPanel.vue';
import VectraLogo from 'src/components/home/VectraLogo.vue';

// --- DEFINITIONS ---
defineOptions({
  name: 'MainLayout',
});

const { locale, t } = useI18n({ useScope: 'global' });
const { themePreference, setParams } = useTheme();

// --- STATE ---
const leftDrawerOpen = ref(false);
const rightDrawerOpen = ref(false);
const showFixStorageDialog = ref(false);
const rightDrawerTab = ref('notifications'); // 'notifications' | 'debug'
const notificationStore = useNotificationStore();
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const socketStore = useSocketStore();

const connectorStore = useConnectorStore();
const { notify } = useNotification();

/**
 * Updates the application language and persists the choice to the backend.
 * @param {string} lang - The language code (e.g. 'en-US', 'fr')
 */
async function setLanguage(lang: string) {
  locale.value = lang;
  try {
    // Only admins can persist global settings
    if (authStore.isAdmin) {
      await settingsService.updateBatch([
        { key: 'app_language', value: lang, group: 'general', is_secret: false },
      ]);
    }
  } catch (err) {
    console.error('Failed to persist language preference', err);
  }
}

// État réactif pour stocker les couleurs actuelles du logo
// Initialisé avec les couleurs par défaut
const currentColors = reactive({
  left: '#2A4B7C',
  right: '#b08989',
  mid: '#a6a5a5',
});

// --- COMPUTED ---

const isHomePage = computed(() => route.path === '/');

const themeIcon = computed(() => {
  if (themePreference.value === 'auto') return 'brightness_auto';
  return themePreference.value === 'dark' ? 'dark_mode' : 'light_mode';
});

// --- FUNCTIONS ---
function toggleTheme() {
  // Cycle: auto -> light -> dark -> auto
  // Or simplified: light <-> dark (treating auto as dark preference if system is dark??)
  // Let's go with a simple binary toggle for now, defaulting to 'light' if current is 'auto' (or checking logic).

  // Logic: If currently dark (explicit or auto-resolved), go light. Else go dark.
  // Since we only have access to preference here easily without checking matchMedia again (though useTheme handles it),
  // let's just cycle explicitly: Light -> Dark -> Auto -> Light...
  // Or simpler: Light <-> Dark.

  if (themePreference.value === 'light') {
    void setParams('dark');
  } else {
    void setParams('light');
  }
}

/**
 * Toggles the visibility of the right drawer.
 * @param {'notifications' | 'debug'} tab - The tab to open (optional)
 */
function toggleRightDrawer(tab?: string) {
  if (tab) {
    // If drawer is closed, open it to the tab
    if (!rightDrawerOpen.value) {
      rightDrawerOpen.value = true;
      rightDrawerTab.value = tab;
    } else {
      // If drawer is open
      if (rightDrawerTab.value === tab) {
        // Same tab clicked: close it
        rightDrawerOpen.value = false;
      } else {
        // Different tab clicked: switch tab
        rightDrawerTab.value = tab;
      }
    }
  } else {
    // Default toggle (e.g. close button)
    rightDrawerOpen.value = !rightDrawerOpen.value;
  }

  if (rightDrawerOpen.value && rightDrawerTab.value === 'notifications') {
    void notificationStore.fetchNotifications();
  }
}

/**
 * Logs out the current user and redirects to login.
 */
async function logout() {
  authStore.logout();
  await router.push('/login');
}

// --- LIFECYCLE ---

onMounted(() => {
  if (authStore.isAuthenticated) {
    void socketStore.initConnection();

    // Admin-only data fetching
    if (authStore.isAdmin) {
      void notificationStore.fetchNotifications();
      // Ensure connectors are loaded to know the status
      void connectorStore.fetchAll(true);
    }

    window.addEventListener('doc-update', handleDocUpdate);
  }
});

onUnmounted(() => {
  window.removeEventListener('doc-update', handleDocUpdate);
});

/**
 * Handles real-time document status updates via custom event.
 * Shows a notification if ingestion fails.
 * @param {Event} event - The doc-update custom event.
 */
function handleDocUpdate(event: Event) {
  const detail = (event as CustomEvent).detail;
  if (detail.status === 'failed' || detail.status === 'error') {
    // Group notifications by connector or just global "ingestion-error" group

    // Check for specific functional errors to show as warnings
    const isWarning =
      detail.code === 'csv_id_column_missing' || detail.code === 'csv_id_column_not_unique';
    const type = isWarning ? 'warning' : 'negative';
    const message = isWarning
      ? t('validationError')
      : t('ingestionFailedForDoc', { name: detail.id });

    // Use the localized error message from the backend if possible, or fallback
    // Usually backend sends english technical string, we might want to map it if we have codes
    let caption = detail.details || t('unknownError');
    if (detail.code && t(detail.code) !== detail.code) {
      // use translation if available for the code
      caption = t(detail.code);
    }

    notify({
      type: type,
      group: 'ingestion-failure',
      message: message,
      caption: caption,
      timeout: isWarning ? 8000 : 5000,
      actions: [{ label: t('close'), color: 'white' }],
    });
  }
}
</script>

<style scoped>
.border-bottom {
  border-bottom: 1px solid var(--q-third);
}
.active-menu-item {
  background-color: var(--q-hover-bg); /* Swapped: Lighter for active */
  color: var(--q-text-main) !important;
  border-radius: 4px;
  margin: 0 8px;
}
/* Remove default Quasar hover background */
.menu-item :deep(.q-focus-helper) {
  display: none;
}
.menu-item {
  border-radius: 4px;
  margin: 0 8px;
  color: var(--q-icon-color);
}
.menu-item:not(.active-menu-item):hover {
  background-color: var(--q-hover-bg);
  color: var(--q-text-main);
}
/* Ensure ripple doesn't overflow the rounded corners */
.q-item {
  border-radius: 8px;
  margin: 0 8px;
}
.user-profile-bar {
  background-color: var(--q-primary); /* Standard Discord User Area */
  border-radius: 8px;
  border: 1px solid var(--q-fourth);
}
.status-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--q-secondary); /* Match background */
}
.storage-badge {
  position: absolute;
  bottom: -2px;
  left: -2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--q-secondary); /* Match background */
}
.hover-white:hover {
  color: var(--q-text-main) !important;
  background-color: var(--q-hover-bg); /* Darker hover for buttons */
}

.vectra-brand-name {
  font-size: 2.5em;
  font-weight: 700;
  color: var(--q-text-main);
  letter-spacing: 0.5px;
  padding-left: 4px;
}

.chat-header-portal {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 1;
}

.chat-header-portal > * {
  pointer-events: auto;
}
</style>
