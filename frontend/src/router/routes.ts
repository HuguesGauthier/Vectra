import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('pages/LoginPage.vue'),
  },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'Home', component: () => import('pages/HomePage.vue') },
      {
        path: 'chat',
        name: 'ChatSelection',
        component: () => import('pages/ChatSelectionPage.vue'),
      },
      {
        path: 'chat/:assistant_id',
        name: 'Chat',
        component: () => import('src/modules/chat/views/ChatPage.vue'),
      },

      // Admin Routes
      {
        path: 'admin/dashboard',
        name: 'Dashboard',
        component: () => import('pages/DashboardPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/connectors',
        name: 'Connectors',
        component: () => import('pages/ConnectorsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/connectors/:id/documents',
        name: 'ConnectorDocuments',
        component: () => import('pages/ConnectorDocumentsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/assistants',
        name: 'Assistants',
        component: () => import('pages/AssistantsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/settings',
        name: 'Settings',
        component: () => import('pages/SettingsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: false },
      },
      {
        path: 'admin/users',
        name: 'Users',
        component: () => import('pages/AdminUsersPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'admin/analytics',
        name: 'AdvancedAnalytics',
        component: () => import('pages/AdvancedAnalyticsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
    ],
  },

  // Standalone/Embed Routes
  {
    path: '/embed',
    component: () => import('layouts/StandaloneLayout.vue'),
    children: [
      {
        path: 'chat/:assistant_id',
        name: 'EmbedChat',
        component: () => import('src/modules/chat/views/ChatPage.vue'),
      },
    ],
  },

  // Legacy share route - now redirects to embed view
  {
    path: '/share/:assistant_id',
    redirect: (to) => {
      const id = Array.isArray(to.params.assistant_id)
        ? to.params.assistant_id[0]
        : to.params.assistant_id;
      return `/embed/chat/${id}`;
    },
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
