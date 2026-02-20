import { computed, type Ref, isRef, ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from 'boot/axios';

import geminiLogo from 'src/assets/gemini_logo.svg';
import openaiLogo from 'src/assets/openai_logo.svg';
import localLogo from 'src/assets/local_logo.svg';
import cohereLogo from 'src/assets/cohere.png';
import mistralLogo from 'src/assets/m-rainbow.svg';
import anthropicLogo from 'src/assets/claude.svg';
import type { ProviderOption, ModelInfo } from 'src/models/ProviderOption';

export interface ProviderInfo {
  id: string;
  name: string;
  type: string;
  description?: string;
  configured: boolean;
  is_active: boolean;
  supported_models?: Record<string, unknown>[];
  supported_transcription_models?: Record<string, unknown>[];
}

/**
 * Composable for AI provider options
 * Single source of truth for embedding and chat engine providers
 * Now Backend-Driven!
 */
export function useAiProviders(settings?: Ref<Record<string, string>> | Record<string, string>) {
  const { t } = useI18n();
  const providers = ref<ProviderInfo[]>([]);
  const isLoading = ref(false);

  const fetchProviders = async () => {
    try {
      isLoading.value = true;
      const { data } = await api.get<ProviderInfo[]>('/providers');
      providers.value = data;
    } catch (e) {
      console.error('Failed to fetch providers', e);
    } finally {
      isLoading.value = false;
    }
  };

  // Fetch on mount
  onMounted(() => {
    void fetchProviders();
  });

  const embeddingProviderOptions = computed<ProviderOption[]>(() => {
    // Helper to safely get setting value
    const getSetting = (key: string) => {
      if (!settings) return '';
      // Handle both Ref and direct object
      const s = isRef(settings) ? settings.value : settings;
      return s[key] || '';
    };

    return providers.value
      .filter((p) => p.type === 'embedding')
      .map((p) => {
        let logo = localLogo;
        if (p.id === 'gemini') logo = geminiLogo;
        if (p.id === 'openai') logo = openaiLogo;
        if (p.id === 'ollama') logo = localLogo; // Reuse local logo for Ollama
        if (p.id === 'mistral') logo = mistralLogo;

        // Custom Description based on model name in settings (Hybrid approach)
        let description = ''; // Only show model info if configured, otherwise empty (tagline handles base desc)
        if (p.id === 'local' && getSetting('local_embedding_model')) {
          description = `${t('modelLabel')}: ${getSetting('local_embedding_model')}`;
        } else if (p.id === 'gemini' && getSetting('gemini_embedding_model')) {
          description = `${t('modelLabel')}: ${getSetting('gemini_embedding_model')}`;
        } else if (p.id === 'openai' && getSetting('openai_embedding_model')) {
          description = `${t('modelLabel')}: ${getSetting('openai_embedding_model')}`;
        } else if (p.id === 'ollama' && getSetting('ollama_embedding_model')) {
          description = `${t('modelLabel')}: ${getSetting('ollama_embedding_model')}`;
        }

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline: p.description || undefined, // undefined matches better if optional
          description: description || undefined,
          badge: p.id === 'local' || p.id === 'ollama' ? t('private') : t('public'),
          badgeColor: p.id === 'local' || p.id === 'ollama' ? 'warning' : 'info',
          disabled: !p.configured,
          supported_models: (p.supported_models || []) as unknown as ModelInfo[],
          supported_transcription_models: (p.supported_transcription_models ||
            []) as unknown as ModelInfo[],
        };
      });
  });

  const chatProviderOptions = computed<ProviderOption[]>(() => {
    // Helper to safely get setting value
    const getSetting = (key: string) => {
      if (!settings) return '';
      // Handle both Ref and direct object
      const s = isRef(settings) ? settings.value : settings;
      return s[key] || '';
    };

    return providers.value
      .filter((p) => p.type === 'chat')
      .map((p) => {
        let logo = localLogo;
        if (p.id === 'gemini') logo = geminiLogo;
        if (p.id === 'openai') logo = openaiLogo;
        if (p.id === 'mistral') logo = mistralLogo;
        if (p.id === 'anthropic') logo = anthropicLogo;
        if (p.id === 'ollama') logo = localLogo;

        // Custom Description
        let description = '';
        if (p.id === 'gemini' && getSetting('gemini_chat_model')) {
          description = `${t('modelLabel')}: ${getSetting('gemini_chat_model')}`;
        } else if (p.id === 'openai' && getSetting('openai_chat_model')) {
          description = `${t('modelLabel')}: ${getSetting('openai_chat_model')}`;
        } else if (p.id === 'mistral' && getSetting('mistral_chat_model')) {
          description = `${t('modelLabel')}: ${getSetting('mistral_chat_model')}`;
        } else if (p.id === 'anthropic' && getSetting('anthropic_chat_model')) {
          description = `${t('modelLabel')}: ${getSetting('anthropic_chat_model')}`;
        } else if (p.id === 'ollama' && getSetting('ollama_chat_model')) {
          description = `${t('modelLabel')}: ${getSetting('ollama_chat_model')}`;
        }

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline: p.description || undefined,
          description: description || undefined,
          badge: p.id === 'ollama' ? t('private') : t('public'),
          badgeColor: p.id === 'ollama' ? 'warning' : 'info',
          disabled: !p.configured,
          supported_models: (p.supported_models || []) as unknown as ModelInfo[],
        };
      });
  });

  const rerankProviderOptions = computed<ProviderOption[]>(() => {
    return providers.value
      .filter((p) => p.type === 'rerank')
      .map((p) => {
        let logo = localLogo;
        if (p.id === 'cohere') logo = cohereLogo;
        if (p.id === 'local') logo = localLogo;

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline: p.description || undefined,
          description: undefined,
          badge: p.id === 'local' ? t('private') : t('public'),
          badgeColor: p.id === 'local' ? 'warning' : 'info',
          disabled: !p.configured,
          supported_models: (p.supported_models || []) as unknown as ModelInfo[],
        };
      });
  });

  /**
   * Get the display label for a chat provider value
   */
  const getChatProviderLabel = (value: string | undefined): string => {
    if (!value) return '';
    const option = chatProviderOptions.value.find(
      (opt) => opt.value?.toLowerCase() === value.toLowerCase(),
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

  /**
   * Get the display label for a rerank provider value
   */
  const getRerankProviderLabel = (value: string | undefined): string => {
    if (!value) return '';
    const option = rerankProviderOptions.value.find((opt) => opt.value === value);
    return option?.label || value;
  };

  return {
    providers,
    isLoading,
    fetchProviders,
    embeddingProviderOptions,
    chatProviderOptions,
    rerankProviderOptions,
    getChatProviderLabel,
    getEmbeddingProviderLabel,
    getRerankProviderLabel,
  };
}
