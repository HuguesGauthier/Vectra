import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import {
  connectorDocumentService,
  type ConnectorDocument,
} from '../services/connectorDocumentService';
import { DocStatus } from '../models/enums';

interface PaginationState {
  sortBy: string;
  descending: boolean;
  page: number;
  rowsPerPage: number;
  rowsNumber: number;
}

export const useConnectorDocumentStore = defineStore('connectorDocument', {
  state: () => ({
    documents: [] as (ConnectorDocument & { status_details?: string })[],
    loading: false,
    error: null as string | null,
    search: '',
    pagination: {
      sortBy: 'created_at',
      descending: true,
      page: 1,
      rowsPerPage: 20,
      rowsNumber: 0,
    } as PaginationState,
    currentConnectorId: null as string | null,
    pricing: {} as Record<string, number>, // Add pricing state
  }),

  actions: {
    // ... existing actions ...

    updateDocumentStatus(
      docId: string,
      status: DocStatus,
      tokens?: number,
      vectors?: number,
      updatedAt?: string,
      details?: string,
      lastVectorizedAt?: string,
    ) {
      const index = this.documents.findIndex((d) => d.id === docId);
      if (index !== -1) {
        const doc = this.documents[index];
        if (!doc) return;

        // Create a new object to ensure reactivity
        this.documents[index] = {
          ...doc,
          status: status,
          doc_token_count: tokens !== undefined ? tokens : doc.doc_token_count,
          vector_point_count: vectors !== undefined ? vectors : doc.vector_point_count,
          updated_at: updatedAt !== undefined ? updatedAt : doc.updated_at,
          last_vectorized_at:
            lastVectorizedAt !== undefined ? lastVectorizedAt : doc.last_vectorized_at,
          status_details: details !== undefined ? details : doc.status_details,
        } as ConnectorDocument & { status_details?: string };
      }
    },

    async fetchPricing() {
      try {
        const response = await api.get('/pricing/pricing');
        this.pricing = response.data;
      } catch (error) {
        console.warn('Failed to fetch pricing config:', error);
      }
    },

    getCost(tokens: number, modelName?: string): number {
      const pricePer1k =
        (modelName && this.pricing[modelName]) || this.pricing['default'] || 0.000025; // Fallback

      return (tokens / 1000) * pricePer1k;
    },

    async fetchDocuments(connectorId: string, page?: number, size?: number) {
      if (connectorId !== this.currentConnectorId) {
        // Reset state when switching connectors
        this.currentConnectorId = connectorId;
        this.search = '';
        this.pagination.page = 1;
        this.documents = [];
      }

      this.loading = true;
      this.error = null;

      try {
        const currentPage = page || this.pagination.page;
        const currentSize = size || this.pagination.rowsPerPage;

        const data = await connectorDocumentService.getDocuments(
          connectorId,
          currentPage,
          currentSize,
          undefined, // status filter could be added to state if needed
          this.search,
        );

        // Ensure pricing is loaded (lazy load once)
        if (Object.keys(this.pricing).length === 0) {
          void this.fetchPricing();
        }

        this.documents = data.items;
        this.pagination.page = data.page;
        this.pagination.rowsPerPage = data.size;
        this.pagination.rowsNumber = data.total;
      } catch (err: unknown) {
        console.error('Failed to load documents', err);
        this.error = 'Failed to load documents';
      } finally {
        this.loading = false;
      }
    },

    setSearch(term: string) {
      this.search = term;
      this.pagination.page = 1; // Reset to first page on new search
    },

    async syncDocument(connectorId: string, documentId: string) {
      await connectorDocumentService.syncDocument(connectorId, documentId);
      // Optimistic update
      const doc = this.documents.find((d) => d.id === documentId);
      if (doc) {
        doc.status = DocStatus.PENDING;
      }
    },

    async deleteDocument(connectorId: string, documentId: string) {
      await connectorDocumentService.deleteDocument(connectorId, documentId);
      // Refresh list after delete
      await this.fetchDocuments(connectorId);
    },

    updateDocumentProgress(docId: string, processed: number, total: number) {
      const doc = this.documents.find((d) => d.id === docId);
      if (doc) {
        doc.chunks_processed = processed;
        doc.chunks_total = total;
      }
    },

    onDocumentCreated(doc: ConnectorDocument) {
      if (this.currentConnectorId && doc.connector_id !== this.currentConnectorId) return;
      // Avoid duplicate
      if (this.documents.some((d) => d.id === doc.id)) return;

      this.documents.unshift(doc);
      this.pagination.rowsNumber++;
    },

    onDocumentDeleted(docId: string) {
      const index = this.documents.findIndex((d) => d.id === docId);
      if (index !== -1) {
        this.documents.splice(index, 1);
        this.pagination.rowsNumber--;
      }
    },

    onDocumentUpdated(doc: ConnectorDocument) {
      const index = this.documents.findIndex((d) => d.id === doc.id);
      if (index !== -1) {
        this.documents[index] = { ...this.documents[index], ...doc };
      }
    },
  },
});
