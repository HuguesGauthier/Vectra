import { defineStore } from 'pinia';

export interface SystemMetrics {
  cpu: number;
  memory: number;
  cpu_process: number;
  memory_process: number;
  timestamp: number;
}

export interface ConnectStats {
  active_pipelines: number;
  total_connectors: number;
  system_status: 'ok' | 'error';
  storage_status?: 'online' | 'offline';
  storage_path?: string;
  last_sync_time: string | null;
}

export interface VectorizeStats {
  total_vectors: number;
  total_tokens: number;
  indexing_success_rate: number;
  failed_docs_count: number;
}

export interface ChatStats {
  monthly_sessions: number;
  avg_latency_ttft: number;
  total_tokens_used: number;
}

export interface DashboardStats {
  connect: ConnectStats;
  vectorize: VectorizeStats;
  chat: ChatStats;
}

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    metricsHistory: [] as SystemMetrics[],
    totalQueries: 0,
    ingestionProgress: 0,
    maxHistoryLength: 20, // Keep last 20 points roughly 10 mins
    // BI Metrics
    totalVectors: 0,
    estimatedCost: 0,
    timeSaved: 0,
    // Real-time Dashboard Stats
    stats: null as DashboardStats | null,
    lastUpdated: null as number | null,
    isUpdating: false,
  }),

  actions: {
    async fetchStats() {
      try {
        const { dashboardService } = await import('src/services/dashboardService');
        const stats = await dashboardService.getStats();
        this.updateStats(stats);
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      }
    },

    addSystemMetrics(cpu: number, memory: number, cpu_process = 0, memory_process = 0) {
      const point = {
        cpu,
        memory,
        cpu_process,
        memory_process,
        timestamp: Date.now(),
      };

      this.metricsHistory.push(point);

      if (this.metricsHistory.length > this.maxHistoryLength) {
        this.metricsHistory.shift();
      }
    },

    setTotalQueries(count: number) {
      this.totalQueries = count;
    },

    incrementQueries() {
      this.totalQueries++;
    },

    setBusinessMetrics(metrics: {
      total_vectors: number;
      estimated_cost: number;
      time_saved_hours: number;
    }) {
      this.totalVectors = metrics.total_vectors;
      this.estimatedCost = metrics.estimated_cost;
      this.timeSaved = metrics.time_saved_hours;
    },

    updateStats(stats: DashboardStats) {
      this.isUpdating = true;
      this.stats = stats;
      this.lastUpdated = Date.now();

      // Reset visual indicator after short delay
      setTimeout(() => {
        this.isUpdating = false;
      }, 300);
    },
  },

  getters: {
    cpuSeries: (state) => {
      return [
        {
          name: 'System',
          data: state.metricsHistory.map((m) => Math.max(0, m.cpu - m.cpu_process)),
        },
        {
          name: 'Vectra',
          data: state.metricsHistory.map((m) => m.cpu_process),
        },
      ];
    },
    memorySeries: (state) => {
      return [
        {
          name: 'System',
          data: state.metricsHistory.map((m) => Math.max(0, m.memory - m.memory_process)),
        },
        {
          name: 'Vectra',
          data: state.metricsHistory.map((m) => m.memory_process),
        },
      ];
    },
    labels: (state) => {
      return state.metricsHistory.map((m) => new Date(m.timestamp).toLocaleTimeString());
    },
  },
});
