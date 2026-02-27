import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import { api } from 'src/boot/axios';
import { connectorService, type Connector } from 'src/services/connectorService';
import type { Assistant } from 'src/services/assistantService';

export interface WizardData {
  identity?: { name?: string; role?: string; targetUser?: string };
  mission?: { objective?: string; ragBehavior?: string };
  style?: { tone?: string; language?: string; format?: string };
  safety?: { securityRules?: string; taboos?: string[] };
}

export function useAssistantForm(initialData?: Partial<Assistant>) {
  const { t } = useI18n();
  const { notifySuccess, notifyError } = useNotification();
  // const { confirm } = useDialog(); // removed unused

  const loading = ref(false);
  const loadingConnectors = ref(false);
  const connectors = ref<Connector[]>([]);
  const isOptimizing = ref(false);

  // Default Initial Data
  const defaultData: Partial<Assistant> = {
    name: '',
    description: '',
    avatar_bg_color: '#E08E45',
    instructions: '',
    model: 'ollama',
    use_reranker: false,
    rerank_provider: 'local',

    top_k_retrieval: 25,
    top_n_rerank: 5,
    similarity_cutoff: 0.5,
    use_semantic_cache: false,
    cache_similarity_threshold: 0.9,
    cache_ttl_seconds: 86400,
    is_enabled: true,
    user_authentication: false,
    linked_connector_ids: [],
    configuration: {
      temperature: 0.1,
      top_p: 1.0,
      max_output_tokens: 4096,
      frequency_penalty: 0.0,
      presence_penalty: 0.0,
      tags: [],
    },
  };

  const formData = ref<Partial<Assistant>>({ ...defaultData, ...initialData });

  // --- CONNECTORS & ACL ---

  const availableTags = computed(() => {
    const tags = new Set<string>();
    const selectedIds = formData.value.linked_connector_ids || [];

    connectors.value
      .filter((c) => selectedIds.includes(c.id))
      .forEach((c) => {
        let acl = c.configuration?.connector_acl;

        if (typeof acl === 'string' && acl.trim().startsWith('[') && acl.trim().endsWith(']')) {
          try {
            const parsed = JSON.parse(acl);
            if (Array.isArray(parsed)) acl = parsed;
          } catch {
            // ignore parse error, treat as string
          }
        }

        if (Array.isArray(acl)) {
          acl.forEach((tag) => tags.add(String(tag)));
        } else if (typeof acl === 'string' && acl) {
          tags.add(acl);
        }
      });
    return Array.from(tags).sort();
  });

  // Watch for connector changes to sync tags
  watch(
    () => formData.value.linked_connector_ids,
    () => {
      // Ensure configuration object exists
      if (!formData.value.configuration) {
        formData.value.configuration = { tags: [] };
      }

      // Auto-sync tags from available tags
      formData.value.configuration.tags = availableTags.value;
    },
    { deep: true },
  );

  async function loadConnectors() {
    loadingConnectors.value = true;
    try {
      connectors.value = await connectorService.getAll();
    } catch (e) {
      console.error('Failed to load connectors', e);
      notifyError(t('failedToLoadConnectors') || 'Failed to load connectors');
    } finally {
      loadingConnectors.value = false;
    }
  }

  // --- WIZARD & OPTIMIZATION ---

  async function optimizeInstructions(instructionText: string) {
    if (!instructionText) return instructionText;

    isOptimizing.value = true;
    try {
      const response = await api.post('/prompts/optimize', {
        instruction: instructionText,
        connector_ids: formData.value.linked_connector_ids,
      });

      notifySuccess(t('instructionsOptimized') || 'Instructions optimized!');
      return response.data.optimized_instruction;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error_code?: string } } };
      if (!err.response?.data?.error_code) {
        notifyError(t('failedToOptimize') || 'Optimization failed');
      }
      throw e;
    } finally {
      isOptimizing.value = false;
    }
  }

  function generatePromptFromWizard(data: WizardData): string {
    let prompt = '';

    // Identity
    if (data.identity) {
      prompt += `# IDENTITY\n`;
      if (data.identity.name) prompt += `Name: ${data.identity.name}\n`;
      if (data.identity.role) prompt += `Role: ${data.identity.role}\n`;
      if (data.identity.targetUser) prompt += `Target User: ${data.identity.targetUser}\n`;
      prompt += '\n';
    }

    // Mission
    if (data.mission) {
      prompt += `# MISSION\n`;
      if (data.mission.objective) prompt += `Objective: ${data.mission.objective}\n`;
      if (data.mission.ragBehavior) {
        prompt += `RAG Behavior: ${data.mission.ragBehavior}\n`;
        // Apply side effects to form data if needed (e.g. similarity cutoff)
        if (data.mission.ragBehavior === 'strict') {
          formData.value.similarity_cutoff = 0.7;
        } else if (data.mission.ragBehavior === 'flexible') {
          formData.value.similarity_cutoff = 0.35;
        }
      }
      prompt += '\n';
    }

    // Style
    if (data.style) {
      prompt += `# STYLE\n`;
      if (data.style.tone) prompt += `Tone: ${data.style.tone}\n`;
      if (data.style.language) prompt += `Language: ${data.style.language}\n`;
      if (data.style.format) prompt += `Format: ${data.style.format}\n`;
      prompt += '\n';
    }

    // Safety
    if (data.safety) {
      prompt += `# SAFETY\n`;
      if (data.safety.securityRules) prompt += `Rules: ${data.safety.securityRules}\n`;
      if (data.safety.taboos && data.safety.taboos.length) {
        prompt += `Taboos: ${data.safety.taboos.join(', ')}\n`;
      }
    }

    notifySuccess(t('promptGenerated') || 'Prompt generated from wizard!');
    return prompt;
  }

  function resetForm() {
    formData.value = JSON.parse(JSON.stringify(defaultData));
    if (initialData) {
      Object.assign(formData.value, JSON.parse(JSON.stringify(initialData)));
    }
  }

  function setFormData(data: Partial<Assistant>) {
    formData.value = JSON.parse(JSON.stringify(data));
    // Ensure nested objects
    if (!formData.value.configuration) {
      formData.value.configuration = { ...defaultData.configuration };
    }
    if (!formData.value.linked_connector_ids) {
      formData.value.linked_connector_ids = [];
    }
  }

  return {
    formData,
    loading,
    loadingConnectors,
    connectors,
    availableTags,
    isOptimizing,
    loadConnectors,
    optimizeInstructions,
    generatePromptFromWizard,
    resetForm,
    setFormData,
    defaultData,
  };
}
