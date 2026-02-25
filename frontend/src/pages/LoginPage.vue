<template>
  <q-layout view="lHh Lpr lFf" class="bg-transparent">
    <NeuralMeshBackground />
    <q-header class="bg-transparent" style="color: var(--q-icon-color); box-shadow: none">
      <q-toolbar>
        <q-space />
        <q-btn-dropdown flat dense icon="language" class="q-mr-sm">
          <q-list>
            <q-item clickable v-close-popup @click="setLanguage('en-US')">
              <q-item-section>{{ $t('langEnglish') }}</q-item-section>
            </q-item>
            <q-item clickable v-close-popup @click="setLanguage('fr')">
              <q-item-section>{{ $t('langFrench') }}</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
        <q-btn flat dense round :icon="themeIcon" @click="toggleTheme">
          <q-tooltip>{{ $t('theme') }}</q-tooltip>
        </q-btn>
      </q-toolbar>
    </q-header>
    <q-page-container class="bg-transparent">
      <q-page class="flex flex-center bg-transparent">
        <q-card class="q-pa-md my_card">
          <q-card-section class="text-center">
            <div class="absolute-top text-center" style="top: -110px">
              <div
                class="inline-block"
                style="width: 160px; height: 160px; border-radius: 50%; overflow: hidden"
              >
                <VectraLogo :disable-animation="true" style="width: 100%; height: 100%" />
              </div>
            </div>
            <div class="q-mt-md"></div>
            <div class="text-h5 text-weight-bold" style="letter-spacing: 0.5px">
              {{ $t('loginTitle') }}
            </div>
          </q-card-section>
          <q-card-section>
            <q-form @submit.prevent="onSubmit" class="q-gutter-md">
              <q-input
                outlined
                bg-color="primary"
                v-model="email"
                :label="$t('email')"
                lazy-rules
                :rules="[(val) => (val && val.length > 0) || $t('pleaseTypeEmail')]"
                autocomplete="username"
                autofocus
              />

              <q-input
                outlined
                bg-color="primary"
                type="password"
                v-model="password"
                :label="$t('password')"
                lazy-rules
                :rules="[(val) => (val && val.length > 0) || $t('pleaseTypePassword')]"
                autocomplete="current-password"
              />

              <div class="column q-gutter-y-sm">
                <q-btn
                  :label="$t('login')"
                  type="submit"
                  color="accent"
                  text-color="white"
                  class="full-width"
                  :loading="loading"
                  unelevated
                  no-ripple
                />

                <div class="row items-center q-my-md">
                  <q-separator class="col" />
                  <div class="q-px-sm text-caption text-grey-5">{{ $t('loginOr') }}</div>
                  <q-separator class="col" />
                </div>

                <q-btn
                  :label="$t('continueAsGuest')"
                  color="primary"
                  text-color="grey-7"
                  class="full-width guest-btn"
                  outline
                  unelevated
                  no-ripple
                  @click="continueAsGuest"
                />
              </div>
            </q-form>
          </q-card-section>
          <q-card-section v-if="error" class="text-negative text-center q-pt-none">
            {{ error }}
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAuthStore } from 'stores/authStore';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import VectraLogo from 'src/components/home/VectraLogo.vue';
import NeuralMeshBackground from 'src/components/login/NeuralMeshBackground.vue';
import { useTheme } from 'src/composables/useTheme';

// --- DEFINITIONS ---
defineOptions({
  name: 'LoginPage',
});

// --- STATE ---
const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const authStore = useAuthStore();
const router = useRouter();
const { t, locale } = useI18n({ useScope: 'global' });
const { notifySuccess } = useNotification();
const { themePreference, setParams } = useTheme();

// --- COMPUTED ---
const themeIcon = computed(() => {
  if (themePreference.value === 'auto') return 'brightness_auto';
  return themePreference.value === 'dark' ? 'dark_mode' : 'light_mode';
});

// --- FUNCTIONS ---

/**
 * Handles login form submission.
 * Authenticates user and redirects to dashboard.
 */
const onSubmit = async () => {
  loading.value = true;
  error.value = '';
  try {
    await authStore.login(email.value, password.value);
    notifySuccess(t('loginSuccessful'));

    // Redirect based on role
    if (authStore.isAdmin) {
      await router.push('/admin/dashboard');
    } else {
      await router.push({ name: 'ChatSelection' });
    }
  } catch (err: unknown) {
    const errorObj = err as { response?: { data?: { error_code?: string } } };

    // If handled by global interceptor, just set the local error text (optional) or do nothing
    // BUT we want to ensure "loginFailed" feedback if global didn't catch it.
    if (!errorObj.response?.data?.error_code) {
      error.value = t('loginFailed');
    }
  } finally {
    loading.value = false;
  }
};

/**
 * Handles guest access by bypassing backend authentication
 * and routing directly to the public chat interface.
 */
const continueAsGuest = async () => {
  await router.push({ name: 'ChatSelection' });
};

/**
 * Updates the application language locally.
 * @param {string} lang - The language code (e.g. 'en-US', 'fr')
 */
function setLanguage(lang: string) {
  locale.value = lang;
}

/**
 * Toggles the application theme locally.
 */
function toggleTheme() {
  if (themePreference.value === 'light') {
    void setParams('dark');
  } else {
    void setParams('light');
  }
}
</script>

<style scoped>
.mesh-bg {
  position: relative;
  background-color: var(--q-secondary);
  background-image:
    radial-gradient(ellipse 60% 80% at 0% 0%, var(--q-primary) 0%, transparent 100%),
    radial-gradient(
      ellipse 160% 120% at 40% -10%,
      transparent 44%,
      var(--q-secondary) 44.5%,
      var(--q-secondary) 100%
    ),
    radial-gradient(ellipse 100% 100% at 30% 0%, var(--q-primary) 0%, transparent 100%),
    radial-gradient(ellipse 80% 80% at 80% 100%, var(--q-primary) 0%, transparent 100%);
  background-attachment: fixed;
  background-size: cover;
}

:deep(.q-layout),
:deep(.q-layout__container),
:deep(.q-layout__section--main),
:deep(.q-page-container),
:deep(.q-page) {
  background: transparent !important;
}

body.body--light .mesh-bg {
  background-color: #e0e5ec;
  background-image:
    radial-gradient(ellipse 60% 80% at 0% 0%, rgba(255, 255, 255, 0.8) 0%, transparent 100%),
    radial-gradient(
      ellipse 160% 120% at 40% -10%,
      transparent 44%,
      rgba(0, 0, 0, 0.1) 44.5%,
      rgba(0, 0, 0, 0.2) 100%
    ),
    radial-gradient(ellipse 100% 100% at 30% 0%, var(--q-primary) 0%, transparent 100%),
    radial-gradient(ellipse 80% 80% at 80% 100%, var(--q-secondary) 0%, transparent 100%);
  background-attachment: fixed;
  background-size: cover;
}

.my_card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.02) !important;
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  overflow: visible;
  transition: all 0.3s ease;
}

.my_card :deep(.q-card__section) {
  background: transparent !important;
}

body.body--light .my_card {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 16px 40px rgba(31, 38, 135, 0.1);
}

body.body--light .my_card :deep(.q-field__control) {
  background: rgba(255, 255, 255, 0.6) !important;
}

body.body--dark .my_card :deep(.q-field__control) {
  background: var(--q-primary) !important;
}

body.body--dark .my_card :deep(.q-field__control:before) {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

body.body--dark .guest-btn {
  background: var(--q-primary) !important;
}

body.body--light .text-grey-5 {
  color: #888 !important;
}
</style>
