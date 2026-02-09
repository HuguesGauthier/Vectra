<template>
  <div class="q-pa-none fit relative-position bg-secondary">
    <q-card
      v-if="store.notifications.length === 0"
      class="flex items-center justify-center q-pa-xs bg-secondary"
      flat
    >
      <q-avatar icon="notifications_none" size="50px" />
      <div class="text-h6 text-weight-bold">
        {{ $t('noNotifications') || 'No new notifications' }}
      </div>
    </q-card>

    <q-list>
      <q-item
        v-for="notification in store.notifications"
        :key="notification.id"
        clickable
        v-ripple
        class="transition-colors"
        :class="{ 'bg-secondary': !notification.read }"
        @click="markRead(notification.id)"
      >
        <q-item-section avatar>
          <q-icon :name="getIcon(notification.type)" :color="getColor(notification.type)" />
        </q-item-section>

        <q-item-section>
          <div class="text-weight-medium">
            {{ notification.message }}
          </div>
          <div class="text-caption q-mt-xs">
            {{ formatDate(notification.created_at) }}
          </div>
        </q-item-section>

        <q-item-section side v-if="!notification.read">
          <q-badge color="accent" rounded p class="shadow-1" />
        </q-item-section>
      </q-item>
    </q-list>
  </div>
</template>

<script setup lang="ts">
import { useNotificationStore } from 'src/stores/notificationStore';
import { date } from 'quasar';

const store = useNotificationStore();

function getIcon(type: string) {
  switch (type) {
    case 'positive':
      return 'check_circle';
    case 'negative':
      return 'error';
    case 'warning':
      return 'warning';
    case 'info':
    default:
      return 'info';
  }
}

function getColor(type: string) {
  switch (type) {
    case 'positive':
      return 'positive';
    case 'negative':
      return 'negative';
    case 'warning':
      return 'warning';
    case 'info':
    default:
      return 'info';
  }
}

function formatDate(dt: string) {
  return date.formatDate(dt, 'YYYY-MM-DD HH:mm');
}

function markRead(id: string) {
  void store.markAsRead(id);
}
</script>
