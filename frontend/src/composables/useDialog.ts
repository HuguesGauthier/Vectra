import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  confirmColor?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel?: () => void;
}

export function useDialog() {
  const $q = useQuasar();
  const { t } = useI18n();

  function confirm(options: ConfirmOptions) {
    $q.dialog({
      title: options.title,
      message: options.message,
      cancel: {
        label: options.cancelLabel || t('cancel'),
        color: 'third',
        flat: true,
      },
      persistent: true,
      ok: {
        label: options.confirmLabel || t('confirm'),
        color: options.confirmColor || 'primary',
        flat: true,
      },
    })
      .onOk(() => {
        options.onConfirm();
      })
      .onCancel(() => {
        if (options.onCancel) {
          options.onCancel();
        }
      });
  }

  return {
    confirm,
  };
}
