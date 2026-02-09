<template>
  <q-layout view="lHh Lpr lFf">
    <q-page-container>
      <q-page class="flex flex-center bg-primary">
        <q-card class="q-pa-md shadow-5 my_card" bordered>
          <q-card-section class="text-center">
            <div class="absolute-top text-center" style="top: -110px">
              <div
                class="inline-block"
                style="width: 160px; height: 160px; border-radius: 50%; overflow: hidden"
              >
                <VectraLogo :disable-animation="true" style="width: 100%; height: 100%" />
              </div>
            </div>
            <div class="q-mt-lg"></div>
            <div class="text-h5 text-weight-bold">{{ $t('loginTitle') }}</div>
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

              <div>
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
import { ref } from 'vue';
import { useAuthStore } from 'stores/authStore';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import VectraLogo from 'src/components/home/VectraLogo.vue';

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
const { t } = useI18n();
const { notifySuccess } = useNotification();

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
</script>

<style scoped>
.my_card {
  width: 100%;
  max-width: 400px;
  background: radial-gradient(circle at center, var(--q-primary) 0%, var(--q-secondary) 100%);
  border-radius: 15px;
  overflow: visible;
}
</style>
