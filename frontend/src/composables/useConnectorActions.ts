import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { connectorService } from 'src/services/connectorService';
import type { Connector, ConnectorSavePayload } from 'src/models/Connector';
import { ConnectorStatus, ConnectorType } from 'src/models/enums';
import { useDialog } from 'src/composables/useDialog';
import { useNotification } from 'src/composables/useNotification';
import { useConnectorStore } from 'src/stores/ConnectorStore';

export function useConnectorActions() {
  const { t } = useI18n();
  const { confirm } = useDialog();
  const { notifySuccess, notifyWarning, notifyBackendError } = useNotification();
  const connectorStore = useConnectorStore();

  const isSaving = ref(false);

  /**
   * Refreshes the list of connectors in the store.
   */
  const loadConnectors = async (silent = false) => {
    await connectorStore.fetchAll(silent);
  };

  /**
   * Main save handler that includes complex business logic validation
   * (e.g. path change confirmation, recursive disable confirmation).
   */
  const handleSaveConnector = async (
    payload: ConnectorSavePayload,
    originalConnector: Connector | null,
    onSuccess: () => void,
  ) => {
    // 1. Check for Path Change on Folder/File Connector
    if (
      originalConnector &&
      originalConnector.connector_type === ConnectorType.LOCAL_FILE &&
      payload.type === 'folder'
    ) {
      const oldPath = originalConnector.configuration?.path;
      const newPath = payload.data.configuration?.path;

      if (oldPath && newPath && oldPath !== newPath) {
        confirm({
          title: t('confirmPathChange'),
          message: t('confirmPathChangeMessage'),
          confirmLabel: t('confirm'),
          confirmColor: 'warning',
          onConfirm: () => {
            void processSave(payload, originalConnector, true, onSuccess);
          },
        });
        return;
      }

      const oldRecursive = originalConnector.configuration?.recursive;
      const newRecursive = payload.data.configuration?.recursive;

      // 2. Check if Recursive was disabled
      if (oldRecursive === true && newRecursive === false) {
        confirm({
          title: t('confirmRecursiveDisable'),
          message: t('confirmRecursiveDisableMessage'),
          confirmLabel: t('confirm'),
          confirmColor: 'warning',
          onConfirm: () => {
            void processSave(payload, originalConnector, true, onSuccess);
          },
        });
        return;
      }
    }

    // Default save path
    await processSave(payload, originalConnector, false, onSuccess);
  };

  /**
   * Internal function to execute the actual save API call.
   */
  const processSave = async (
    payload: ConnectorSavePayload,
    originalConnector: Connector | null,
    autoScan: boolean,
    onSuccess: () => void,
  ) => {
    isSaving.value = true;
    try {
      const {
        name,
        description,
        schedule_type,
        schedule_cron,
        configuration,
        chunk_size,
        chunk_overlap,
      } = payload.data;
      let savedId: string | undefined;

      if (originalConnector) {
        // UPDATE
        savedId = originalConnector.id;
        await connectorService.update(originalConnector.id, {
          name: name || originalConnector.name,
          description:
            description !== undefined ? description : originalConnector.description || '',
          connector_type: payload.data.connector_type,
          configuration: configuration,
          schedule_type: schedule_type,
          schedule_cron: schedule_cron,
          chunk_size: chunk_size,
          chunk_overlap: chunk_overlap,
        });
        notifySuccess(t('connectorUpdated', { name: name || originalConnector.name }));
      } else {
        // CREATE
        const created = await connectorService.create({
          name: name || `New ${payload.type} Connector`,
          description: description || '',
          connector_type: payload.data.connector_type,
          configuration,
          schedule_type: schedule_type,
          schedule_cron: schedule_cron,
          chunk_size: chunk_size,
          chunk_overlap: chunk_overlap,
        });
        savedId = created.id;
        notifySuccess(t('connectorCreated', { name: name || `New ${payload.type} Connector` }));
      }

      // Success Callback (close drawer, etc)
      onSuccess();

      // Refresh list
      await loadConnectors();

      // Auto Scan if flagged
      if (autoScan && savedId) {
        console.log('Triggering auto-scan due to path change...');
        await connectorService.scanFiles(savedId);
        notifySuccess(t('scanStarted', { name: name }));
      }
    } catch {
      // Notification handled by global interceptor usually
    } finally {
      isSaving.value = false;
    }
  };

  /**
   * Handles deletion with confirmation.
   */
  const handleDeleteConnector = (connector: Connector) => {
    confirm({
      title: t('confirmDeletion'),
      message: t('confirmDeletionMessage', { name: connector.name }),
      confirmLabel: t('delete'),
      confirmColor: 'negative',
      onConfirm: () => {
        void (async () => {
          try {
            await connectorService.delete(connector.id);
            notifySuccess(t('connectorDeleted', { name: connector.name }));
            await loadConnectors();
          } catch {
            // Global interceptor usually handles this
          }
        })();
      },
    });
  };

  /**
   * Toggles enabled/disabled state.
   */
  const handleToggleConnector = async (source: Connector, val: boolean | null) => {
    const newValue = !!val;
    // Optimistic update
    source.is_enabled = newValue;
    if (!newValue) {
      source.status = ConnectorStatus.IDLE;
    }

    try {
      await connectorService.update(source.id, { is_enabled: newValue });
      const msg = t('sourceToggled', {
        name: source.name,
        status: newValue ? t('enabled') : t('disabled'),
      });
      if (newValue) notifySuccess(msg);
      else notifyWarning(msg);
    } catch (error) {
      // Revert optimism
      source.is_enabled = !newValue;
      notifyBackendError(error, t('failedToSave'));
    }
  };

  /**
   * Triggers manual sync.
   */
  const handleSyncConnector = async (source: Connector, force = false) => {
    if (source.status === ConnectorStatus.SYNCING || source.status === ConnectorStatus.QUEUED) {
      // Stop
      try {
        await connectorService.stop(source.id);
        notifyWarning(t('syncStopped', { name: source.name }));
      } catch {
        // Global interceptor
      }
      return;
    }

    // Start
    try {
      await connectorService.sync(source.id, force);
      const msg = force ? t('forceSyncStarted') : t('syncStarted', { name: source.name });
      notifySuccess(msg);
      source.status = ConnectorStatus.QUEUED;
    } catch {
      // Global interceptor
    }
  };

  /**
   * Triggers manual file scan.
   */
  const handleScanFiles = async (source: Connector) => {
    try {
      await connectorService.scanFiles(source.id);
      notifySuccess(t('scanStarted', { name: source.name }));
    } catch (error) {
      notifyBackendError(error, t('failedToScan'));
    }
  };

  return {
    isSaving,
    loadConnectors,
    handleSaveConnector,
    handleDeleteConnector,
    handleToggleConnector,
    handleSyncConnector,
    handleScanFiles,
  };
}
