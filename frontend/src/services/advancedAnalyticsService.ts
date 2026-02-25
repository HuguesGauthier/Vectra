/**
 * Advanced Analytics API Service
 */
import { api } from 'boot/axios';

export interface TTFTPercentiles {
  p50: number;
  p95: number;
  p99: number;
  period_hours: number;
}

export interface StepBreakdown {
  step_name: string;
  avg_duration: number;
  step_count: number;
  avg_tokens?: {
    input: number;
    output: number;
  };
}

export interface CacheMetrics {
  hit_rate: number;
  total_requests: number;
  cache_hits: number;
  cache_misses: number;
  period_hours: number;
}

// User Satisfaction KPIs
export interface SessionDistribution {
  session_type: string;
  session_count: number;
  percentage: number;
}

export interface TrendingTopic {
  canonical_text: string;
  frequency: number;
  variation_count: number;
  last_asked: string;
}

export interface TopicDiversity {
  diversity_score: number;
  total_topics: number;
  dominant_topic_share: number;
}

// Cost & ROI KPIs
export interface AssistantCost {
  assistant_id: string;
  assistant_name: string;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
}

export interface DocumentUtilization {
  file_name: string;
  connector_name: string;
  retrieval_count: number;
  last_retrieved: string | null;
  status: string;
}

// Knowledge Base Health KPIs
export interface DocumentFreshness {
  freshness_category: string;
  doc_count: number;
  percentage: number;
}

export interface RerankingImpact {
  avg_score_improvement: number;
  reranking_enabled_count: number;
  avg_position_change: number | null;
}

export interface ConnectorSyncRate {
  connector_id: string;
  connector_name: string;
  success_rate: number;
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  avg_sync_duration: number | null;
}

export interface UserStat {
  user_id: string;
  email: string;
  full_name: string;
  total_tokens: number;
  interaction_count: number;
  last_active: string | null;
}

export interface AdvancedAnalytics {
  ttft_percentiles?: TTFTPercentiles;
  step_breakdown: StepBreakdown[];
  cache_metrics?: CacheMetrics;
  trending_topics: TrendingTopic[];
  topic_diversity?: TopicDiversity;
  assistant_costs: AssistantCost[];
  document_freshness: DocumentFreshness[];
  session_distribution: SessionDistribution[];
  document_utilization: DocumentUtilization[];
  reranking_impact?: RerankingImpact;
  connector_sync_rates: ConnectorSyncRate[];
  user_stats: UserStat[];
  generated_at: string;
}

class AdvancedAnalyticsService {
  /**
   * Get comprehensive advanced analytics
   */
  async getAdvancedAnalytics(params?: {
    assistant_id?: string;
    ttft_hours?: number;
    step_days?: number;
    cache_hours?: number;
    cost_hours?: number;
    trending_limit?: number;
  }): Promise<AdvancedAnalytics> {
    const response = await api.get<AdvancedAnalytics>('/analytics/advanced', { params });
    return response.data;
  }

  /**
   * Get TTFT percentiles only
   */
  async getTTFTPercentiles(hours: number = 24): Promise<TTFTPercentiles> {
    const response = await api.get<TTFTPercentiles>(`/analytics/ttft`, {
      params: { hours },
    });
    return response.data;
  }

  /**
   * Get trending topics
   */
  async getTrendingTopics(assistant_id?: string, limit: number = 10): Promise<TrendingTopic[]> {
    const response = await api.get<TrendingTopic[]>(`/analytics/trending`, {
      params: { assistant_id, limit },
    });
    return response.data;
  }

  /**
   * Get assistant costs
   */
  async getAssistantCosts(hours: number = 24): Promise<AssistantCost[]> {
    const response = await api.get<AssistantCost[]>(`/analytics/costs`, {
      params: { hours },
    });
    return response.data;
  }

  /**
   * Get document freshness
   */
  async getDocumentFreshness(): Promise<DocumentFreshness[]> {
    const response = await api.get<DocumentFreshness[]>(`/analytics/freshness`);
    return response.data;
  }
}

export default new AdvancedAnalyticsService();
