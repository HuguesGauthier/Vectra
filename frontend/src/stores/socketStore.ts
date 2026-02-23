import { defineStore } from 'pinia';
import { useConnectorStore } from './ConnectorStore';
import { useConnectorDocumentStore } from './ConnectorDocumentStore';
import { useDashboardStore } from './dashboardStore';
import { useAdvancedAnalyticsStore } from './advancedAnalyticsStore';
import type { ConnectorStatus, DocStatus } from '../models/enums';

import type { Connector } from '../models/Connector';

import type { ConnectorDocument } from '../services/connectorDocumentService';
import type { AdvancedAnalytics } from '../services/advancedAnalyticsService';

// Define strict types for WS messages
interface ConnectorStatusMsg {
  type: 'CONNECTOR_STATUS';
  id: string;
  status: ConnectorStatus;
}

interface ConnectorProgressMsg {
  type: 'CONNECTOR_PROGRESS';
  id: string;
  current: number;
  total: number;
  percent: number;
}

interface DocUpdateMsg {
  type: 'DOC_UPDATE';
  id: string;
  status: DocStatus;
  details?: string;
  doc_token_count?: number;
  vector_point_count?: number;
  updated_at?: string;
  last_vectorized_at?: string;
}

interface WorkerStatusMsg {
  type: 'WORKER_STATUS';
  status: 'online' | 'offline';
}

interface DocProgressMsg {
  type: 'DOC_PROGRESS';
  doc_id: string;
  processed: number;
  total: number;
}

interface DocCreatedMsg {
  type: 'DOC_CREATED';
  data: ConnectorDocument;
}

interface DocDeletedMsg {
  type: 'DOC_DELETED';
  id: string;
  connector_id?: string;
}

interface DocUpdatedMsg {
  type: 'DOC_UPDATED';
  data: ConnectorDocument;
}

interface ConnectorCreatedMsg {
  type: 'CONNECTOR_CREATED';
  data: Connector;
}

interface ConnectorUpdatedMsg {
  type: 'CONNECTOR_UPDATED';
  data: Connector;
}

interface ConnectorDeletedMsg {
  type: 'CONNECTOR_DELETED';
  id: string;
}

interface DashboardStatsMsg {
  type: 'DASHBOARD_STATS';
  data: {
    connect: {
      active_pipelines: number;
      total_connectors: number;
      system_status: 'ok' | 'error';
      storage_status: 'online' | 'offline';
      last_sync_time: string | null;
    };
    vectorize: {
      total_vectors: number;
      total_tokens: number;
      indexing_success_rate: number;
      failed_docs_count: number;
    };
    chat: {
      monthly_sessions: number;
      avg_latency_ttft: number;
      total_tokens_used: number;
      avg_feedback_score: number;
    };
  };
}

interface AdvancedAnalyticsMsg {
  type: 'ADVANCED_ANALYTICS_STATS';
  data: AdvancedAnalytics;
}

export type WSMessage =
  | ConnectorStatusMsg
  | ConnectorProgressMsg
  | DocUpdateMsg
  | WorkerStatusMsg
  | DocProgressMsg
  | DocCreatedMsg
  | DocDeletedMsg
  | DocUpdatedMsg
  | ConnectorCreatedMsg
  | ConnectorUpdatedMsg
  | ConnectorDeletedMsg
  | DashboardStatsMsg
  | AdvancedAnalyticsMsg;

const throttleMap = new Map<string, number>();

export const useSocketStore = defineStore('socket', {
  state: () => ({
    isConnected: false,
    isWorkerOnline: false,
    storageStatus: 'online' as 'online' | 'offline',
    socket: null as WebSocket | null,
    reconnectInterval: 500,
  }),

  actions: {
    handleDocProgressThrottled(payload: DocProgressMsg) {
      const now = Date.now();
      const last = throttleMap.get(payload.doc_id) || 0;
      // Throttle to 100ms, but always allow 100% completion
      if (now - last > 100 || payload.processed === payload.total) {
        window.dispatchEvent(new CustomEvent('doc-progress', { detail: payload }));
        throttleMap.set(payload.doc_id, now);
      }
    },

    /**
     * Initializes the WebSocket connection.
     * Implements reconnection logic with exponential backoff.
     */
    initConnection() {
      if (
        this.socket &&
        (this.socket.readyState === WebSocket.OPEN ||
          this.socket.readyState === WebSocket.CONNECTING)
      ) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host; // includes port if not 80/443
      const wsUrl = `${protocol}//${host}/api/v1/ws`;

      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.isConnected = true;
        this.reconnectInterval = 1000; // Reset backoff
        // Request immediate worker status update
        this.socket?.send('get_worker_status');
      };

      this.socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as WSMessage;
          this.handleMessage(payload);
          // Debug hook
          window.dispatchEvent(new CustomEvent('ws-debug', { detail: payload }));
        } catch (e) {
          console.error('[WS] Failed to parse message', e);
        }
      };

      this.socket.onclose = () => {
        this.isConnected = false;
        this.socket = null;
        this.scheduleReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('[WS] Error', error);
        this.socket?.close();
      };
    },

    /**
     * Schedules a reconnection attempt with exponential backoff (max 30s).
     */
    scheduleReconnect() {
      setTimeout(() => {
        this.initConnection();
        this.reconnectInterval = Math.min(this.reconnectInterval * 2, 30000); // Max 30s backoff
      }, this.reconnectInterval);
    },

    /**
     * Dispatches incoming WebSocket messages to appropriate sinks.
     * Updates stores (ConnectorStore) or dispatches global events.
     *
     * @param {WSMessage} payload - The parsed message payload.
     */
    handleMessage(payload: WSMessage) {
      const connectorStore = useConnectorStore();

      switch (payload.type) {
        case 'CONNECTOR_STATUS':
          connectorStore.updateConnectorStatus(payload.id, payload.status);
          break;

        case 'CONNECTOR_PROGRESS':
          connectorStore.updateProgress(payload.id, payload.current, payload.total);
          break;

        case 'CONNECTOR_CREATED':
          connectorStore.onConnectorCreated(payload.data);
          break;

        case 'CONNECTOR_UPDATED':
          connectorStore.onConnectorUpdated(payload.data);
          break;

        case 'CONNECTOR_DELETED':
          connectorStore.onConnectorDeleted(payload.id);
          break;

        case 'DOC_CREATED':
          {
            const docStore = useConnectorDocumentStore();
            docStore.onDocumentCreated(payload.data);

            // Also update connector count
            // connectorStore.incrementDocCount(payload.data.connector_id);
          }
          break;

        case 'DOC_DELETED':
          {
            const docStore = useConnectorDocumentStore();
            docStore.onDocumentDeleted(payload.id);

            // Also update connector count
            // connectorStore.decrementDocCount(payload.connector_id);
          }
          break;

        case 'DOC_UPDATED':
          {
            const docStore = useConnectorDocumentStore();
            docStore.onDocumentUpdated(payload.data);
          }
          break;

        case 'DOC_UPDATE':
          {
            const msg: DocUpdateMsg = payload;
            const docStore = useConnectorDocumentStore();

            // 1. Dispatch event for legacy component listeners
            window.dispatchEvent(new CustomEvent('doc-update', { detail: payload }));

            // 2. Direct Store Update (More reliable)
            docStore.updateDocumentStatus(
              msg.id,
              msg.status,
              msg.doc_token_count,
              msg.vector_point_count,
              msg.updated_at,
              msg.details,
              msg.last_vectorized_at,
            );

            // 3. Update processing state for global progress bar
            if (msg.status === 'processing') {
              connectorStore.setDocProcessing(msg.id, true);
            } else if (['indexed', 'failed', 'stopped', 'skipped', 'paused'].includes(msg.status)) {
              connectorStore.setDocProcessing(msg.id, false);
            }
          }
          break;

        case 'DOC_PROGRESS':
          this.handleDocProgressThrottled(payload);
          break;

        case 'WORKER_STATUS':
          this.isWorkerOnline = payload.status === 'online';
          break;

        case 'DASHBOARD_STATS':
          {
            const dashboardStore = useDashboardStore();
            dashboardStore.updateStats(payload.data);

            // Update storage status also
            if (payload.data.connect.storage_status) {
              this.storageStatus = payload.data.connect.storage_status;
            }
          }
          break;

        case 'ADVANCED_ANALYTICS_STATS':
          {
            const analyticsStore = useAdvancedAnalyticsStore();
            analyticsStore.updateStats(payload.data);
          }
          break;
      }
    },
  },
});
