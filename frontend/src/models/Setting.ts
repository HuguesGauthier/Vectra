export interface Setting {
  key: string;
  value: string;
  group: string;
  is_secret: boolean;
  description?: string;
}

export interface SettingUpdate {
  key: string;
  value: string;
  group: string;
  is_secret: boolean;
}
