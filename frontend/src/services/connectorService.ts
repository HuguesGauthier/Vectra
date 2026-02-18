import { api } from 'boot/axios';
import type { ConnectorType, ScheduleType } from '../models/enums';

const API_PATH = '/connectors';

export interface Connector {
  id: string;
  name: string;
  connector_type: ConnectorType;
  configuration: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  // UI helpers
  icon?: string;
  color?: string;
  description?: string;
  schedule_cron?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ConnectorCreatePayload {
  name: string;
  description?: string;
  connector_type: ConnectorType;
  configuration: Record<string, unknown>;
  schedule_type?: ScheduleType;
  schedule_cron?: string | undefined;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ConnectorUpdatePayload {
  name?: string;
  description?: string;
  connector_type?: ConnectorType;
  configuration?: Record<string, unknown>;
  schedule_type?: ScheduleType;
  schedule_cron?: string | undefined;
  is_enabled?: boolean;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ConnectorDocument {
  id: string;
  connector_id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  status: string;
  created_at: string;
  updated_at: string;
  doc_token_count?: number;
  vector_point_count?: number;
  chunks_total?: number;
  chunks_processed?: number;
}

export interface ConnectorDocumentsResponse {
  items: ConnectorDocument[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const connectorService = {
  /**
   * Fetches all connectors.
   * @returns {Promise<Connector[]>} List of all connectors.
   */
  async getAll(): Promise<Connector[]> {
    const response = await api.get(API_PATH + '/');
    return response.data;
  },

  /**
   * Creates a new connector.
   * @param {ConnectorCreatePayload} payload - The creation payload.
   * @returns {Promise<Connector>} The created connector.
   */
  async create(payload: ConnectorCreatePayload): Promise<Connector> {
    const response = await api.post(`${API_PATH}/`, payload);
    return response.data;
  },

  /**
   * Updates an existing connector.
   * @param {string} id - The connector ID.
   * @param {ConnectorUpdatePayload} payload - Fields to update.
   * @returns {Promise<Connector>} The updated connector.
   */
  async update(id: string, payload: ConnectorUpdatePayload): Promise<Connector> {
    const response = await api.put(`${API_PATH}/${id}`, payload);
    return response.data;
  },

  /**
   * Deletes a connector.
   * @param {string} id - The connector ID to delete.
   */
  async delete(id: string): Promise<void> {
    await api.delete(`${API_PATH}/${id}`);
  },

  /**
   * Uploads a file to the server (for File connectors).
   * @param {File} file - The file object to upload.
   * @returns {Promise<string>} The path where the file was saved.
   */
  async uploadFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/system/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.path;
  },

  /**
   * Triggers a synchronization for a connector.
   * @param {string} id - The connector ID.
   * @param {boolean} force - If true, forces a full re-sync (clearing old vectors).
   */
  async sync(id: string, force: boolean = false): Promise<void> {
    const url = force ? `${API_PATH}/${id}/sync?force=true` : `${API_PATH}/${id}/sync`;
    await api.post(url);
  },

  /**
   * Signals a connector to stop its current operation.
   * @param {string} id - The connector ID.
   */
  async stop(id: string): Promise<void> {
    await api.post(`${API_PATH}/${id}/stop`);
  },

  /**
   * Triggers a file scan for a folder connector.
   * @param {string} id - The connector ID.
   */
  async scanFiles(id: string): Promise<void> {
    await api.post(`${API_PATH}/${id}/scan-files`);
  },

  /**
   * Deletes a temporary uploaded file.
   * Used when user cancels connector creation after uploading.
   * @param {string} filePath - The path to the temporary file.
   */
  async deleteTempFile(filePath: string): Promise<void> {
    await api.delete('/system/temp-file', { data: { path: filePath } });
  },

  /**
   * Fetches paginated documents for a connector.
   *
   * @param {string} id - The connector ID.
   * @param {number} page - Page number (1-based).
   * @param {number} size - Page size.
   * @param {string} [status] - Filter by document status.
   * @param {string} [search] - Search string for filename filtering.
   * @returns {Promise<ConnectorDocumentsResponse>} Paginated response.
   */
  async getDocuments(
    id: string,
    page: number = 1,
    size: number = 20,
    status?: string,
    search?: string,
  ): Promise<ConnectorDocumentsResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
    });

    if (status) params.append('status', status);
    if (search) params.append('search', search);

    const response = await api.get(`${API_PATH}/${id}/documents?${params.toString()}`);
    return response.data;
  },

  /**
   * Deletes a specific document from a connector.
   * @param {string} connectorId - The connector ID.
   * @param {string} documentId - The document ID.
   */
  async deleteDocument(connectorId: string, documentId: string): Promise<void> {
    await api.delete(`${API_PATH}/${connectorId}/documents/${documentId}`);
  },

  /**
   * Triggers a sync for a specific document.
   * @param {string} connectorId - The connector ID.
   * @param {string} documentId - The document ID.
   */
  async syncDocument(connectorId: string, documentId: string): Promise<void> {
    await api.post(`${API_PATH}/${connectorId}/documents/${documentId}/sync`);
  },
};
