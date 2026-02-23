import { boot } from 'quasar/wrappers';
import axios, { type AxiosInstance } from 'axios';
import { Notify } from 'quasar';
import { useNotificationStore } from 'stores/notificationStore';
import { useAuthStore } from 'stores/authStore';

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Helper to normalize axios error to Error object
 */
const wrapError = (error: unknown): Error =>
  error instanceof Error ? error : new Error(String(error));

export default boot(({ app, router }) => {
  app.config.globalProperties.$axios = axios;
  app.config.globalProperties.$api = api;

  // Request interceptor: Add auth token to every request
  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(wrapError(error)),
  );

  // Response interceptor: Global Error Handling
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      const { config, response } = error;

      // 0. Handle Internal Polls (Notifications)
      // Failed notification polls shouldn't kill the session or spam UI
      if (config?.url?.includes('/notifications')) {
        return Promise.reject(wrapError(error));
      }

      // 1. Handle Network Errors (no response)
      if (!response) {
        Notify.create({
          type: 'negative',
          message: 'Network Error - API may be restarting or unreachable',
          position: 'bottom-right',
          timeout: 5000,
          actions: [{ label: 'Dismiss', color: 'white' }],
        });

        return Promise.reject(wrapError(error));
      }

      const { status, data } = response;
      const $t = app.config.globalProperties.$t;

      // 2. Authentication (401) or Forbidden (403)
      if (status === 401 || status === 403) {
        const authStore = useAuthStore();
        authStore.logout();

        const requiresAuth = router.currentRoute.value.meta.requiresAuth;
        if (requiresAuth && router.currentRoute.value.path !== '/login') {
          void router.push('/login');
        }
      }

      // 3. Functional Errors (4xx)
      else if (status >= 400 && status < 500) {
        const errorCode = data.code || data.error_code;
        let message = '';

        if (errorCode) {
          const translationKey = `errors.${errorCode}`;
          const translatedMessage = $t(translationKey);

          message = (translatedMessage && translatedMessage !== translationKey)
            ? translatedMessage
            : (data.message || `Error (${errorCode})`);
        } else {
          message = data.message || 'Validation Error';
        }

        Notify.create({
          type: 'warning',
          message: message,
          icon: 'warning',
          position: 'bottom-right',
        });

        const store = useNotificationStore();
        void store.addNotification({
          type: 'warning',
          message: message,
          read: false,
        });
      }

      // 4. Technical Errors (5xx)
      else {
        const errorId = data.id || data.error_id || 'N/A';
        const errorCode = data.code || data.error_code || 'unknown_error';
        const techMsg = `Erreur Système [${errorCode}] - ID: ${errorId}`;

        Notify.create({
          type: 'negative',
          message: techMsg,
          icon: 'report_problem',
          timeout: 0,
          position: 'bottom-right',
          actions: [{ label: 'Dismiss', color: 'white' }],
        });

        const store = useNotificationStore();
        void store.addNotification({
          type: 'negative',
          message: techMsg,
          read: false,
        });
      }

      return Promise.reject(wrapError(error));
    },
  );
});

export { api };

