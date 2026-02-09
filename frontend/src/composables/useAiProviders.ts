import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

/**
 * Composable for AI provider options
 * Single source of truth for embedding and chat engine providers
 */
export function useAiProviders() {
  const { t } = useI18n();

  const embeddingProviderOptions = computed(() => [
    { label: t('gemini'), value: 'gemini' },
    { label: t('openai'), value: 'openai' },
    { label: t('localEmbedding'), value: 'local' },
  ]);

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
    return option?.label || value;
  };

  return {
    embeddingProviderOptions,
    chatProviderOptions,
    getChatProviderLabel,
    getEmbeddingProviderLabel,
  };
}
