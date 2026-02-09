import { defineStore } from 'pinia';
import { ref } from 'vue';

export interface Source {
  id: string;
  name: string;
  type: 'pdf' | 'docx' | 'txt' | 'web' | 'audio';
  content?: string;
  url?: string;
  filePath?: string;
  metadata?: Record<string, unknown>;
}

export const usePublicChatStore = defineStore('publicChat', () => {
  const isDrawerOpen = ref(false);
  const selectedSources = ref<Source[]>([]);
  const fontSize = ref(14); // Default 14px
  const currentAssistantColor = ref('orange-8'); // Default fallback

  function toggleDrawer() {
    isDrawerOpen.value = !isDrawerOpen.value;
  }

  function increaseFontSize() {
    if (fontSize.value < 32) fontSize.value += 2;
  }

  function decreaseFontSize() {
    if (fontSize.value > 10) fontSize.value -= 2;
  }

  function openDrawerWithSources(sources: Source[]) {
    selectedSources.value = sources;
    isDrawerOpen.value = true;
  }

  function clearSources() {
    selectedSources.value = [];
    isDrawerOpen.value = false;
  }

  async function resetSession(sessionId: string) {
    if (!sessionId) return;
    try {
      await fetch(`http://localhost:8000/api/v1/chat/${sessionId}`, {
        method: 'DELETE',
      });
    } catch (error) {
      console.error('Failed to reset session:', error);
    }
  }

  return {
    isDrawerOpen,
    selectedSources,
    fontSize,
    increaseFontSize,
    decreaseFontSize,
    currentAssistantColor,
    toggleDrawer,
    openDrawerWithSources,
    clearSources,
    resetSession,
  };
});
