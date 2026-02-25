import { api } from 'boot/axios';
import type { DashboardStats } from 'src/stores/dashboardStore';

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },
};
