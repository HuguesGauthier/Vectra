import { api } from 'boot/axios';

const API_PATH = '/connectors';

export interface ConnectorDocument {
  id: string;
  connector_id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  status: string;
  created_at: string;
  updated_at: string;
  last_vectorized_at?: string;
  doc_token_count?: number;
  vector_point_count?: number;
  chunks_total?: number;
  chunks_processed?: number;
  configuration?: Record<string, unknown>;
}

export interface ConnectorDocumentCreate {
  file_path: string;
  file_name: string;
  file_size?: number;
  configuration?: Record<string, unknown>;
}

export interface ConnectorDocumentsResponse {
  items: ConnectorDocument[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const connectorDocumentService = {
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

  async createDocument(id: string, payload: ConnectorDocumentCreate): Promise<ConnectorDocument> {
    const response = await api.post(`${API_PATH}/${id}/documents`, payload);
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

  /**
   * Uploads a file to the server (for File connectors).
   * @param {File} file - The file object to upload.
   * @returns {Promise<string>} The path where the file was saved.
   */
  async uploadFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/system/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.path;
  },
  async updateDocument(
    connectorId: string,
    documentId: string,
    data: { file_name?: string; file_path?: string; configuration?: Record<string, unknown> },
  ): Promise<ConnectorDocument> {
    const response = await api.put<ConnectorDocument>(
      `/connectors/${connectorId}/documents/${documentId}`,
      data,
    );
    return response.data;
  },
  /**
   * Stops the sync for a specific document.
   * @param {string} connectorId - The connector ID.
   * @param {string} documentId - The document ID.
   */
  async stopDocument(connectorId: string, documentId: string): Promise<void> {
    await api.post(`${API_PATH}/${connectorId}/documents/${documentId}/stop`);
  },
};
