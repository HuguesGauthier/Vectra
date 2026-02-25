import { defineStore } from 'pinia';
import { connectorService } from '../services/connectorService';
import { Connector } from '../models/Connector';
import type { ConnectorStatus } from '../models/enums';

export const useConnectorStore = defineStore('connector', {
  state: () => ({
    connectors: [] as Connector[],
    selectedConnector: null as Connector | null,
    loading: false,
    error: null as string | null,
    processingDocIds: new Set<string>(),
  }),

  getters: {
    // Helper to find a connector by ID
    getConnectorById: (state) => (id: string) => {
      // Logic to handle UUID vs String if needed, usually string exact match
      return state.connectors.find((c) => c.id === id);
    },

    // Check if any connector is currently vectorizing OR if any single doc is processing
    isVectorizing: (state) => {
      const activeStatuses = ['syncing', 'queued', 'vectorizing', 'starting'];
      return (
        state.connectors.some((c) => activeStatuses.includes(c.status)) ||
        state.processingDocIds.size > 0
      );
    },
  },

  actions: {
    setDocProcessing(id: string, isProcessing: boolean) {
      if (isProcessing) {
        this.processingDocIds.add(id);
      } else {
        this.processingDocIds.delete(id);
      }
    },
    async fetchAll(silent = false) {
      if (!silent) this.loading = true;
      this.error = null;
      try {
        const data = await connectorService.getAll();
        this.connectors = data.map((c) => new Connector(c));
      } catch (err: unknown) {
        // Ignore 401 errors as they are handled by global interceptor (redirect to login)
        if (err && typeof err === 'object' && 'response' in err) {
          const response = (err as { response: { status: number } }).response;
          if (response && response.status === 401) {
            return;
          }
        }

        console.error('Failed to load connectors', err);
        const message = err instanceof Error ? err.message : 'Failed to load connectors';
        this.error = message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    updateConnectorStatus(id: string, status: ConnectorStatus) {
      const connector = this.connectors.find((c) => c.id === id);
      if (connector) {
        // Cast string to enum if necessary
        connector.status = status;
        if (status === 'idle') {
          connector.last_vectorized_at = new Date().toISOString();
        }
      }
    },

    updateProgress(id: string, current: number, total: number) {
      const connector = this.connectors.find((c) => c.id === id);
      if (connector) {
        connector.sync_current = current;
        connector.sync_total = total;
      }
    },

    onConnectorCreated(data: Partial<Connector>) {
      // Avoid duplicate
      if (this.connectors.some((c) => c.id === data.id)) return;
      this.connectors.unshift(new Connector(data));
    },

    onConnectorUpdated(data: Partial<Connector>) {
      const index = this.connectors.findIndex((c) => c.id === data.id);
      if (index !== -1) {
        // Merge updates or replace
        // We use Object.assign to keep the instance or replace it.
        // It's cleaner to replace usually, but we want to keep some transient state if any?
        // Actually, replacing with new Connector(data) is safest.
        this.connectors.splice(index, 1, new Connector(data));
      } else {
        // If we don't have it, treat as created? Or ignore.
        // Let's add it if missing, sync-like behavior.
        this.connectors.unshift(new Connector(data));
      }
    },

    onConnectorDeleted(id: string) {
      const index = this.connectors.findIndex((c) => c.id === id);
      if (index !== -1) {
        this.connectors.splice(index, 1);
      }
    },

    incrementDocCount(connectorId: string) {
      const connector = this.connectors.find((c) => c.id === connectorId);
      if (connector) {
        connector.total_docs_count = (connector.total_docs_count || 0) + 1;
      }
    },

    decrementDocCount(connectorId: string) {
      const connector = this.connectors.find((c) => c.id === connectorId);
      if (connector) {
        connector.total_docs_count = Math.max((connector.total_docs_count || 0) - 1, 0);
      }
    },
  },
});
