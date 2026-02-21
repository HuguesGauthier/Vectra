<template>
  <q-page class="bg-primary q-pa-lg q-pt-xl">
    <!-- Assistants Selection -->

    <!-- Loading State -->
    <div v-if="loading" class="row justify-center q-pa-xl">
      <q-spinner-dots size="50px" color="accent" />
    </div>

    <!-- Empty State -->
    <div v-else-if="assistants.length === 0" class="column flex-center text-center q-pa-xl">
      <q-icon name="psychology" size="100px" color="grey-7" class="q-mb-md" />
      <div class="text-h5 text-grey-5 q-mb-xs">{{ $t('noAssistantsForChat') }}</div>
      <div class="text-subtitle2 text-grey-7 q-mb-lg">
        {{ $t('createAssistantToChat') }}
      </div>
      <q-btn
        unelevated
        color="accent"
        text-color="grey-3"
        icon="add"
        :label="$t('createNew')"
        @click="goToAssistantsPage"
      />
    </div>

    <!-- Assistants Grid -->
    <div v-else class="row q-col-gutter-xl justify-center">
      <div
        v-for="assistant in assistants"
        :key="assistant.id"
        class="col-12 col-sm-6 col-md-4"
        style="max-width: 400px"
      >
        <AssistantSelectionCard
          :assistant="assistant"
          @select="selectAssistant(assistant)"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { assistantService, type Assistant } from 'src/services/assistantService';
import AssistantSelectionCard from 'src/components/assistants/AssistantSelectionCard.vue';

defineOptions({
  name: 'ChatSelectionPage',
});

// --- STATE ---
const router = useRouter();

const assistants = ref<Assistant[]>([]);
const loading = ref(true);

// --- LIFECYCLE ---
onMounted(async () => {
  await loadAssistants();
});

// --- FUNCTIONS ---

/**
 * Loads all available assistants
 */
async function loadAssistants() {
  loading.value = true;
  try {
    assistants.value = await assistantService.getAll();
  } catch (error) {
    console.error('Failed to load assistants:', error);
  } finally {
    loading.value = false;
  }
}


/**
 * Navigates to the chat page with the selected assistant
 */
function selectAssistant(assistant: Assistant) {
  void router.push({ name: 'Chat', params: { assistant_id: assistant.id } });
}

/**
 * Navigates to the assistants page to create a new assistant
 */
function goToAssistantsPage() {
  void router.push({ name: 'Assistants' });
}
</script>

<style scoped>
/* Minimalist selection page styles */
</style>

