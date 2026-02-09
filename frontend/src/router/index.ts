import { defineRouter } from '#q-app/wrappers';
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router';
import routes from './routes';

import { useAuthStore } from 'stores/authStore';

/*
 * If not building with SSR mode, you can
 * directly export the Router instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Router instance.
 */

export default defineRouter(function (/* { store, ssrContext } */) {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : process.env.VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory;

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,

    // Leave this as is and make changes in quasar.conf.js instead!
    // quasar.conf.js -> build -> vueRouterMode
    // quasar.conf.js -> build -> publicPath
    history: createHistory(process.env.VUE_ROUTER_BASE),
  });

  Router.beforeEach((to, from, next) => {
    const authStore = useAuthStore();

    // Check if route requires auth
    if (to.meta.requiresAuth) {
      if (!authStore.isAuthenticated) {
        next({ name: 'Login', query: { redirect: to.fullPath } });
        return;
      }

      // Check for Admin role if required
      if (to.meta.requiresAdmin) {
        if (!authStore.isAdmin) {
          next({ name: 'ChatSelection' }); // Redirect to home/chat selection
          return;
        }
      }
    }

    // Redirect if already logged in and visiting login
    if (to.name === 'Login' && authStore.isAuthenticated) {
      next({ name: 'Dashboard' });
      return;
    }

    next();
  });

  return Router;
});
