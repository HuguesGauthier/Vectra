import { useQuasar } from 'quasar';
import { useNotificationStore } from 'src/stores/notificationStore';

export interface NotificationOptions {
  type: 'positive' | 'negative' | 'warning' | 'info';
  message: string;
  caption?: string;
  timeout?: number;
  icon?: string;
  group?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  actions?: any[];
}

export function useNotification() {
  const $q = useQuasar();
  const store = useNotificationStore();

  function notify(options: NotificationOptions) {
    // Display Quasar notification
    const notifyOptions = {
      progress: true,
      timeout: 2500,
      position: 'top' as const,
      ...options,
      classes: 'rounded-notification glossy',
    };

    // Dark text for positive notifications (better contrast with pastel green)
    if (options.type === 'positive') {
      Object.assign(notifyOptions, { textColor: 'dark' });
    }

    $q.notify(notifyOptions);

    // Persist to backend and history
    // Map Quasar types to our backend types if needed, or use same string
    const type = options.type || 'info';
    // Only 'negative' (error) and 'warning' should be unread
    const isImportant = type === 'negative' || type === 'warning';

    void store.addNotification({
      type: type,
      message: options.message + (options.caption ? ` (${options.caption})` : ''),
      read: !isImportant,
    });
  }

  function notifySuccess(message: string, caption?: string) {
    const opts: NotificationOptions = { type: 'positive', message, icon: 'check_circle' };
    if (caption) opts.caption = caption;
    notify(opts);
  }

  function notifyError(message: string, caption?: string) {
    const opts: NotificationOptions = { type: 'negative', message, icon: 'error' };
    if (caption) opts.caption = caption;
    notify(opts);
  }

  function notifyWarning(message: string, caption?: string) {
    const opts: NotificationOptions = { type: 'warning', message, icon: 'warning' };
    if (caption) opts.caption = caption;
    notify(opts);
  }

  function notifyInfo(message: string, caption?: string) {
    const opts: NotificationOptions = { type: 'info', message, icon: 'info' };
    if (caption) opts.caption = caption;
    notify(opts);
  }

  function notifyBackendError(error: unknown, fallbackMessage: string, fallbackCaption?: string) {
    const err = error as { response?: { data?: { error_code?: string; detail?: string } } };

    // If handled by global interceptor (has error_code), do nothing (or simpler log)
    // BUT user said "apply the @[doc/frontend_coding_standards.md] ... which says:
    // "Do NOT manually catch and notify for standard API errors ... if the global interceptor handles it"
    // However, sometimes we WANT to handle it manually or the global one is just a catch-all.
    // The previous code often did `if (err.response?.data?.error_code) return;`
    // So this helper should probably do exactly that check to make it one-liner.
    if (err.response?.data?.error_code) {
      return;
    }

    // If not handled globally, show our local fallback
    notifyError(fallbackMessage, fallbackCaption || (err as Error).message || String(error));
  }

  return {
    notify,
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
    notifyBackendError,
  };
}
