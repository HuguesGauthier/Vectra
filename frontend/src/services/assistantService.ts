import { api } from 'boot/axios';

const API_PATH = '/assistants';

export interface AssistantConfig {
  temperature?: number;
  top_p?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
  max_output_tokens?: number;
  tags?: string[]; // Preserved for ACL
  [key: string]: unknown; // Allow other keys but prefer typed ones
}

export interface Assistant {
  id: string;
  name: string;
  description?: string;
  avatar_bg_color?: string;
  avatar_text_color?: string;
  avatar_image?: string;
  avatar_vertical_position?: number;
  instructions: string;
  model?: string;
  use_reranker?: boolean;
  rerank_provider?: string;

  top_k_retrieval?: number;
  retrieval_similarity_cutoff?: number;
  top_n_rerank?: number;
  similarity_cutoff?: number;
  use_semantic_cache?: boolean;
  cache_similarity_threshold?: number;
  cache_ttl_seconds?: number;
  configuration?: AssistantConfig;
  is_enabled?: boolean;
  user_authentication?: boolean;
  created_at?: string;
  updated_at?: string;
  linked_connector_ids?: string[];

  // Full objects for relationship loading
  linked_connectors?: { id: string; name: string }[];
}

export const assistantService = {
  async getAll(): Promise<Assistant[]> {
    const response = await api.get(`${API_PATH}/`);
    return response.data;
  },

  async getById(id: string): Promise<Assistant> {
    const response = await api.get(`${API_PATH}/${id}/`);
    return response.data;
  },

  async create(data: Partial<Assistant>): Promise<Assistant> {
    const response = await api.post(`${API_PATH}/`, data);
    return response.data;
  },

  async update(id: string, data: Partial<Assistant>): Promise<Assistant> {
    const response = await api.put(`${API_PATH}/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`${API_PATH}/${id}`);
  },

  async uploadAvatar(id: string, file: File): Promise<Assistant> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`${API_PATH}/${id}/avatar`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async deleteAvatar(id: string): Promise<Assistant> {
    const response = await api.delete(`${API_PATH}/${id}/avatar`);
    return response.data;
  },

  async clearCache(id: string): Promise<{ deleted_count: number }> {
    const response = await api.delete(`${API_PATH}/${id}/cache`);
    return response.data;
  },

  getAvatarUrl(id: string): string {
    return `${api.defaults.baseURL}${API_PATH}/${id}/avatar`;
  },

  async getAvatarBlob(id: string): Promise<Blob> {
    const response = await api.get(`${API_PATH}/${id}/avatar`, {
      responseType: 'blob',
      params: { t: Date.now() },
    });
    return response.data;
  },
};
