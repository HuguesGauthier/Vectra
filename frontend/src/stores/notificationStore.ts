import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/authStore';

export interface Notification {
  id: string;
  type: 'positive' | 'negative' | 'warning' | 'info';
  message: string;
  read: boolean;
  created_at: string;
}

export interface BackendNotification {
  id: string;
  type: string;
  message: string;
  read: boolean;
  created_at: string;
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([]);
  const unreadCount = ref(0);
  const isLoading = ref(false);

  const API_URL = '/notifications/';

  async function fetchNotifications() {
    const authStore = useAuthStore();
    if (!authStore.token || !authStore.isAdmin) return;

    isLoading.value = true;
    try {
      const response = await api.get(API_URL);

      const reverseTypeMap: Record<string, 'positive' | 'negative' | 'warning' | 'info'> = {
        success: 'positive',
        error: 'negative',
        warning: 'warning',
        info: 'info',
        system: 'info',
      };

      notifications.value = response.data.map((n: BackendNotification) => ({
        ...n,
        type: reverseTypeMap[n.type] || 'info',
      }));

      updateUnreadCount();
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'response' in error) {
        const response = (error as { response: { status: number } }).response;
        if (response && response.status === 401) return;
      }
      console.error('Failed to fetch notifications', error);
    } finally {
      isLoading.value = false;
    }
  }

  async function addNotification(notification: { type: string; message: string; read?: boolean }) {
    // 1. Optimistic UI update (always show locally)
    const validTypes = ['positive', 'negative', 'warning', 'info'] as const;
    const notificationType = (validTypes as readonly string[]).includes(notification.type)
      ? (notification.type as (typeof validTypes)[number])
      : 'info';

    const tempId = Date.now().toString(); // temporary ID
    const localNotification: Notification = {
      id: tempId,
      type: notificationType,
      message: notification.message,
      read: notification.read || false,
      created_at: new Date().toISOString(),
    };
    notifications.value.unshift(localNotification);
    updateUnreadCount();

    // 2. Persist to backend ONLY if authenticated AND admin
    const authStore = useAuthStore();
    if (authStore.token && authStore.isAdmin) {
      try {
        // Map Quasar types to Backend Enums
        const typeMap: Record<string, string> = {
          positive: 'success',
          negative: 'error',
          warning: 'warning',
          info: 'info',
        };

        const response = await api.post(API_URL, {
          type: typeMap[notification.type] || 'info',
          message: notification.message,
          read: notification.read || false,
        });

        // Update the local notification with real data from server (id, created_at)
        const index = notifications.value.findIndex((n) => n.id === tempId);
        if (index !== -1) {
          notifications.value[index] = response.data;
        }
      } catch (error) {
        console.error('Failed to save notification', error);
        // Optional: remove from list if save failed? Or keep as local-only?
        // Choosing to keep it so user sees the message.
      }
    }
  }

  async function markAsRead(id: string) {
    const notification = notifications.value.find((n) => n.id === id);
    if (notification && !notification.read) {
      notification.read = true;
      updateUnreadCount();

      const authStore = useAuthStore();
      if (authStore.token) {
        try {
          await api.put(`${API_URL}${id}/read/`);
        } catch (error) {
          console.error('Failed to mark notification as read', error);
          notification.read = false; // Revert
          updateUnreadCount();
        }
      }
    }
  }

  async function markAllRead() {
    // Optimistic update
    notifications.value.forEach((n) => (n.read = true));
    updateUnreadCount();

    const authStore = useAuthStore();
    if (authStore.token) {
      try {
        await api.put(`${API_URL}read/`);
      } catch (error) {
        console.error('Failed to mark all notifications as read', error);
        // Revert/refresh
        void fetchNotifications();
      }
    }
  }

  async function clearAll() {
    notifications.value = [];
    updateUnreadCount();

    const authStore = useAuthStore();
    if (authStore.token) {
      try {
        await api.delete(API_URL);
      } catch (error) {
        console.error('Failed to clear notifications', error);
      }
    }
  }

  function updateUnreadCount() {
    unreadCount.value = notifications.value.filter((n) => !n.read).length;
  }

  return {
    notifications,
    unreadCount,
    isLoading,
    fetchNotifications,
    addNotification,
    markAsRead,
    markAllRead,
    clearAll,
  };
});
