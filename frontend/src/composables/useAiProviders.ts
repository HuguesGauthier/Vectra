import { computed, type Ref, isRef } from 'vue';
import { useI18n } from 'vue-i18n';

import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';

/**
 * Composable for AI provider options
 * Single source of truth for embedding and chat engine providers
 */
export function useAiProviders(settings?: Ref<Record<string, string>> | Record<string, string>) {
  const { t } = useI18n();

  const embeddingProviderOptions = computed(() => {
    // Helper to safely get setting value
    const getSetting = (key: string) => {
      if (!settings) return '';
      // Handle both Ref and direct object
      const s = isRef(settings) ? settings.value : settings;
      return s[key] || '';
    };

    return [
      {
        id: 'local',
        name: t('localEmbedding'),
        value: 'local',
        label: t('localEmbedding'),
        logo: localLogo,
        tagline: 'Private & Secure',
        description: getSetting('local_embedding_model')
          ? `${t('modelLabel')}: ${getSetting('local_embedding_model')}`
          : t('localEmbeddingsDesc'),
        badge: t('private'),
        badgeColor: 'warning',
        disabled: settings ? !getSetting('local_embedding_model') : false,
      },
      {
        id: 'gemini',
        name: t('gemini'),
        value: 'gemini',
        label: t('gemini'),
        logo: geminiLogo,
        tagline: 'Google DeepMind',
        description: getSetting('gemini_embedding_model')
          ? `${t('modelLabel')}: ${getSetting('gemini_embedding_model')}`
          : t('geminiEmbeddingsDesc'),
        badge: t('public'),
        badgeColor: 'info',
        disabled: settings ? !getSetting('gemini_api_key') : false,
      },
      {
        id: 'openai',
        name: t('openai'),
        value: 'openai',
        label: t('openai'),
        logo: openaiLogo,
        tagline: 'Standard Industry Model',
        description: getSetting('openai_embedding_model')
          ? `${t('modelLabel')}: ${getSetting('openai_embedding_model')}`
          : t('openaiEmbeddingsDesc'),
        badge: t('public'),
        badgeColor: 'info',
        disabled: settings ? !getSetting('openai_api_key') : false,
      },
    ];
  });

  const chatProviderOptions = computed(() => [
    { label: t('gemini'), value: 'gemini' },
    { label: t('openai'), value: 'openai' },
    { label: t('mistral'), value: 'mistral' },
    { label: t('mistralLocal'), value: 'ollama' },
  ]);

  /**
   * Get the display label for a chat provider value
   */
  const getChatProviderLabel = (value: string | undefined): string => {
    if (!value) return '';
    const option = chatProviderOptions.value.find(
      (opt) => opt.value.toLowerCase() === value.toLowerCase(),
    );
    return option?.label || value;
  };

  /**
   * Get the display label for an embedding provider value
   */
  const getEmbeddingProviderLabel = (value: string | undefined): string => {
    if (!value) return '';
    const option = embeddingProviderOptions.value.find((opt) => opt.value === value);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (option as any)?.label || value;
  };

  return {
    embeddingProviderOptions,
    chatProviderOptions,
    getChatProviderLabel,
    getEmbeddingProviderLabel,
  };
}
