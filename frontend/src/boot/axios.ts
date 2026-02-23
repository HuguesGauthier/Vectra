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

// Default to backend URL. In prod use env var.
// Default to backend URL. In prod use env var.
const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || '/api/v1',
  withCredentials: true, // Function to pass cookies to the backend
  headers: {
    'Content-Type': 'application/json',
  },
});

console.log('[Axios] Initialized with Base URL:', api.defaults.baseURL);
console.log('[Axios] Current Origin:', window.location.origin);
console.log('[Axios] Mode:', process.env.MODE);

export default boot(({ app, router }) => {
  app.config.globalProperties.$axios = axios;
  app.config.globalProperties.$api = api;

  // Request interceptor: Add auth token to every request
  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('[Axios] Attaching Token:', token.substring(0, 10) + '...');
      } else {
        console.warn('[Axios] No token found in localStorage');
      }
      return config;
    },
    (error) => {
      return Promise.reject(error instanceof Error ? error : new Error(String(error)));
    },
  );

  // Response interceptor: Global Error Handling
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      // Handle Network Errors (no response)
      if (!error.response) {
        // IGNORE notifications endpoint for zombie checks (P0 user request)
        // Failed notification polls shouldn't kill the session
        if (error.config && error.config.url && error.config.url.includes('/notifications')) {
          return Promise.reject(error instanceof Error ? error : new Error(String(error)));
        }

        const message = 'Network Error - API may be restarting or unreachable';
        Notify.create({
          type: 'negative',
          message: message,
          position: 'bottom-right',
          timeout: 5000,
          actions: [{ label: 'Dismiss', color: 'white' }],
        });

        // Clear state and redirect to login to avoid "zombie" state (P1)
        // This is especially helpful during backend watchfile restarts.
        // const authStore = useAuthStore();
        // authStore.logout();

        // if (router.currentRoute.value.path !== '/login') {
        //   void router.push('/login');
        // }

        return Promise.reject(error instanceof Error ? error : new Error(String(error)));
      }

      const { status, data, config } = error.response;
      const $t = app.config.globalProperties.$t;

      // Prevent infinite loop: If the error comes from /notifications, do not trigger a new notification
      if (config && config.url && config.url.includes('/notifications')) {
        return Promise.reject(error instanceof Error ? error : new Error(String(error)));
      }

      // 1. Authentication (401) or Forbidden (403)
      if (status === 401 || status === 403) {
        console.warn(`[Axios] ${status} Error - Handling session failure`);
        console.warn('Failed Request:', config.url);

        const authStore = useAuthStore();
        authStore.logout();

        // Only redirect to login if the current route explicitly requires authentication
        const requiresAuth = router.currentRoute.value.meta.requiresAuth;
        if (requiresAuth && router.currentRoute.value.path !== '/login') {
          void router.push('/login');
        }
      }

      // 2. Functional Errors (4xx)
      else if (status >= 400 && status < 500) {
        const errorCode = data.code || data.error_code;

        // Try to translate. Logic: if translation returns key, it means missing.
        let message = '';

        if (errorCode) {
          const translationKey = `errors.${errorCode}`;
          const translatedMessage = $t(translationKey);

          // Check if translation exists (Quasar i18n returns key if missing)
          if (translatedMessage && translatedMessage !== translationKey) {
            message = translatedMessage;
          } else {
            // Fallback to backend message if translation missing, or generic
            message = data.message || `Error (${errorCode})`;
          }
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
      // 3. Technical Errors (5xx)
      else {
        // Technical Message: System Error [code] - ID: ...
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

      return Promise.reject(error instanceof Error ? error : new Error(String(error)));
    },
  );
});

export { api };
