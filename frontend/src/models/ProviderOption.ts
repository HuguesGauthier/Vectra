export interface ModelInfo {
  id: string;
  name: string;
  description: string;
  category: 'flagship' | 'balanced' | 'economy' | 'reasoning';
  input_price: number;
  output_price: number;
}

export interface ProviderOption {
  id: string;
  name: string;
  tagline?: string | undefined;
  description?: string | undefined;
  logo: string;
  badge?: string | undefined;
  badgeColor?: string | undefined;
  disabled?: boolean | undefined;
  color?: string | undefined;
  value?: string;
  label?: string;
  supported_models?: ModelInfo[];
  supported_transcription_models?: ModelInfo[];
}
