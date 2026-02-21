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
  supported_models?: ModelInfo[];
  supported_transcription_models?: ModelInfo[];
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

        let modelInfo = '';
        const getModelName = (id: string) => {
          const found = p.supported_models?.find((m: ModelInfo) => String(m.id) === id);
          return found?.name || id;
        };

        if (p.id === 'local' && getSetting('local_embedding_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('local_embedding_model'))}`;
        } else if (p.id === 'gemini' && getSetting('gemini_embedding_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('gemini_embedding_model'))}`;
        } else if (p.id === 'openai' && getSetting('openai_embedding_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('openai_embedding_model'))}`;
        } else if (p.id === 'ollama' && getSetting('ollama_embedding_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('ollama_embedding_model'))}`;
        }

        // Design Metadata
        const colors: Record<string, string> = {
          gemini: 'blue-6',
          openai: 'green-6',
          mistral: 'orange-10',
          anthropic: 'brown-6',
          local: 'blue-grey-8',
          ollama: 'blue-grey-8',
          cohere: 'purple-6',
        };

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline:
            t(`${p.id}Tagline`) !== `${p.id}Tagline`
              ? t(`${p.id}Tagline`)
              : p.description || undefined,
          description: t(`${p.id}Desc`) !== `${p.id}Desc` ? t(`${p.id}Desc`) : undefined,
          modelInfo: modelInfo,
          badge: p.id === 'local' || p.id === 'ollama' ? t('private') : t('public'),
          badgeColor: p.id === 'local' || p.id === 'ollama' ? 'warning' : 'info',
          color: colors[p.id] || 'grey-7',
          disabled: !p.configured,
          supported_models: p.supported_models || [],
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
        let modelInfo = '';
        const getModelName = (id: string) => {
          const found = p.supported_models?.find((m: ModelInfo) => String(m.id) === id);
          return found?.name || id;
        };

        if (p.id === 'gemini' && getSetting('gemini_chat_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('gemini_chat_model'))}`;
        } else if (p.id === 'openai' && getSetting('openai_chat_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('openai_chat_model'))}`;
        } else if (p.id === 'mistral' && getSetting('mistral_chat_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('mistral_chat_model'))}`;
        } else if (p.id === 'anthropic' && getSetting('anthropic_chat_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('anthropic_chat_model'))}`;
        } else if (p.id === 'ollama' && getSetting('ollama_chat_model')) {
          modelInfo = `${t('modelLabel')}: ${getModelName(getSetting('ollama_chat_model'))}`;
        }

        // Design Metadata
        const colors: Record<string, string> = {
          gemini: 'blue-6',
          openai: 'green-6',
          mistral: 'orange-10',
          anthropic: 'brown-6',
          local: 'blue-grey-8',
          ollama: 'blue-grey-8',
          cohere: 'purple-6',
        };

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline:
            t(`${p.id}Tagline`) !== `${p.id}Tagline`
              ? t(`${p.id}Tagline`)
              : p.description || undefined,
          description: t(`${p.id}Desc`) !== `${p.id}Desc` ? t(`${p.id}Desc`) : undefined,
          modelInfo: modelInfo,
          badge: p.id === 'ollama' ? t('private') : t('public'),
          badgeColor: p.id === 'ollama' ? 'warning' : 'info',
          color: colors[p.id] || 'grey-7',
          disabled: !p.configured,
          supported_models: p.supported_models || [],
        };
      });
  });

  const rerankProviderOptions = computed<ProviderOption[]>(() => {
    // Helper to safely get setting value
    const getSetting = (key: string) => {
      if (!settings) return '';
      // Handle both Ref and direct object
      const s = isRef(settings) ? settings.value : settings;
      return s[key] || '';
    };

    return providers.value
      .filter((p) => p.type === 'rerank')
      .map((p) => {
        let logo = localLogo;
        if (p.id === 'cohere') logo = cohereLogo;
        if (p.id === 'local') logo = localLogo;

        // Design Metadata
        const colors: Record<string, string> = {
          gemini: 'blue-6',
          openai: 'green-6',
          mistral: 'orange-10',
          anthropic: 'brown-6',
          local: 'blue-grey-8',
          ollama: 'blue-grey-8',
          cohere: 'purple-6',
        };

        // Custom Description
        let modelDescription = '';
        const getModelName = (id: string) => {
          const found = p.supported_models?.find((m: ModelInfo) => String(m.id) === id);
          return found?.name || id;
        };

        if (p.id === 'local' && getSetting('local_rerank_model')) {
          modelDescription = `${t('modelLabel')}: ${getModelName(getSetting('local_rerank_model'))}`;
        }

        return {
          id: p.id,
          name: p.name,
          value: p.id,
          label: p.name,
          logo: logo,
          tagline:
            t(`${p.id}Tagline`) !== `${p.id}Tagline`
              ? t(`${p.id}Tagline`)
              : p.description || undefined,
          description: t(`${p.id}Desc`) !== `${p.id}Desc` ? t(`${p.id}Desc`) : undefined,
          modelInfo: modelDescription,
          badge: p.id === 'local' ? t('private') : t('public'),
          badgeColor: p.id === 'local' ? 'warning' : 'info',
          color: colors[p.id] || 'grey-7',
          disabled: !p.configured,
          supported_models: p.supported_models || [],
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
    return option?.label || value;
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
