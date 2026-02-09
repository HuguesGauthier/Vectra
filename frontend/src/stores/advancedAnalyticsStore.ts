import { defineStore } from 'pinia';
import advancedAnalyticsService, {
  type AdvancedAnalytics,
} from 'src/services/advancedAnalyticsService';

interface AdvancedAnalyticsState {
  stats: AdvancedAnalytics | null;
  lastUpdated: number | null;
  isUpdating: boolean;
  loading: boolean;
}

export const useAdvancedAnalyticsStore = defineStore('advancedAnalytics', {
  state: (): AdvancedAnalyticsState => ({
    stats: null,
    lastUpdated: null,
    isUpdating: false,
    loading: false,
  }),

  actions: {
    async fetchAnalytics() {
      this.loading = true;
      try {
        const stats = await advancedAnalyticsService.getAdvancedAnalytics({
          ttft_hours: 24,
          step_days: 7,
          cache_hours: 24,
          cost_hours: 24,
          trending_limit: 10,
        });
        this.updateStats(stats);
      } catch (error) {
        console.error('Failed to fetch advanced analytics:', error);
      } finally {
        this.loading = false;
      }
    },

    updateStats(stats: AdvancedAnalytics) {
      this.isUpdating = true;

      // Removed hardcoded limit of 5 to allow dynamic sizing
      if (stats.trending_topics && stats.trending_topics.length > 10) {
        stats.trending_topics = stats.trending_topics.slice(0, 10);
      }

      this.stats = stats;
      this.lastUpdated = Date.now();

      // Visual indicator reset
      setTimeout(() => {
        this.isUpdating = false;
      }, 300);
    },
  },
});
