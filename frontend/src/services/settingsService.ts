import { api } from 'boot/axios';
import type { Setting, SettingUpdate } from 'src/models/Setting';

export const settingsService = {
  async getAll(): Promise<Setting[]> {
    const response = await api.get<Setting[]>('/settings/');
    return response.data;
  },

  async updateBatch(settings: SettingUpdate[]): Promise<Setting[]> {
    const response = await api.put<Setting[]>('/settings/', settings);
    return response.data;
  },
};
