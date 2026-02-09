import { api } from 'boot/axios';

const API_PATH = '/trends'; // Base URL is already /api/v1

export interface TrendingTopic {
  id: string;
  canonical_text: string;
  frequency: number;
  assistant_id: string;
}

export const trendingService = {
  /**
   * Fetches trending topics.
   * @param assistantId - Optional ID to filter by assistant. If null, returns global trends.
   * @param limit - Max number of topics to return (default 5).
   */
  async getTrendingTopics(
    assistantId: string | null = null,
    limit: number = 10,
  ): Promise<TrendingTopic[]> {
    const params: Record<string, string | number> = { limit };
    if (assistantId) {
      params['assistant_id'] = assistantId;
    }

    // Note: The backend endpoint might be /assistants/{id}/trending based on previous context,
    // but the plan mentioned /api/trends. I will implement a flexible approach or stick to the likely backend route.
    // Based on the backend implementation guide, the route was:
    // @router.get("/assistants/{assistant_id}/trending", ...)

    // I should probably use that structure if assistantId is present.
    // If global trends are needed (Dashboard), we might need a new endpoint or adapted logic.
    // For now, let's assume the backend provides a way to get global trends or we iterate.
    // However, the user request said: "The backend now provides an endpoint GET /api/trends?assistant_id=X"
    // So I will stick to the User Request's specification.

    const response = await api.get(API_PATH + '/', { params });
    return response.data;
  },
};
