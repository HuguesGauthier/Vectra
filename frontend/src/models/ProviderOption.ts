export interface ProviderOption {
  id: string;
  name: string;
  tagline?: string | undefined;
  description?: string | undefined;
  logo: string;
  badge?: string | undefined;
  badgeColor?: string | undefined;
  disabled?: boolean | undefined;
  value?: string; // Add value as it is used in map in useAiProviders
  label?: string; // Add label as it is used
}
