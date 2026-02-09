<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Title Header -->
    <div class="row items-center justify-between q-pt-md q-pb-md q-pl-none q-mb-md">
      <div>
        <div class="text-h4 text-weight-bold">{{ $t('selectAssistant') }}</div>
        <div class="text-subtitle1 q-pt-xs">
          {{ $t('selectAssistantDesc') }}
        </div>
      </div>
    </div>

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
    <div v-else class="row q-col-gutter-md justify-center">
      <div
        v-for="assistant in assistants"
        :key="assistant.id"
        class="col-12 col-sm-6 col-md-4"
        style="max-width: 350px"
      >
        <q-card
          flat
          bordered
          class="assistant-card cursor-pointer full-height column text-center"
          @click="selectAssistant(assistant)"
        >
          <q-card-section class="col column items-center justify-center q-pa-lg">
            <!-- Avatar Icon -->
            <q-avatar
              :color="
                assistant.avatar_bg_color &&
                !assistant.avatar_bg_color.startsWith('#') &&
                !assistant.avatar_bg_color.startsWith('rgb')
                  ? assistant.avatar_bg_color
                  : undefined
              "
              :style="
                assistant.avatar_bg_color &&
                (assistant.avatar_bg_color.startsWith('#') ||
                  assistant.avatar_bg_color.startsWith('rgb'))
                  ? { backgroundColor: assistant.avatar_bg_color }
                  : {}
              "
              :text-color="assistant.avatar_text_color || 'white'"
              size="80px"
              class="q-mb-md"
            >
              <img
                v-if="assistant.avatar_image"
                :src="assistantService.getAvatarUrl(assistant.id)"
                style="object-fit: cover"
                :style="{ objectPosition: `center ${assistant.avatar_vertical_position ?? 50}%` }"
              />
              <q-icon v-else name="psychology" />
            </q-avatar>

            <!-- Assistant Name -->
            <div class="text-h5 text-weight-bold text-white q-mb-xs">{{ assistant.name }}</div>

            <!-- Model Tagline -->
            <div class="text-subtitle2 text-accent q-mb-md">
              {{ assistant.model || 'Gemini' }}
            </div>

            <!-- Description -->
            <div class="text-body2 text-grey-5 q-mb-md" style="min-height: 60px">
              {{ assistant.description || $t('noDescription') }}
            </div>

            <!-- Metadata Row -->
            <div class="full-width q-mb-md">
              <div class="row items-center justify-center q-gutter-xs">
                <q-icon name="source" size="16px" class="text-grey-6" />
                <span class="text-caption text-grey-6">
                  {{ getConnectorCount(assistant) }} {{ $t('connectedSources') }}
                </span>
              </div>
            </div>

            <!-- ACL Tags -->
            <div
              v-if="
                assistant.configuration?.tags &&
                Array.isArray(assistant.configuration.tags) &&
                assistant.configuration.tags.length > 0
              "
              class="full-width"
            >
              <div class="row justify-center q-gutter-xs flex-wrap">
                <q-chip
                  v-for="tag in (assistant.configuration.tags as string[]).slice(0, 3)"
                  :key="tag"
                  :label="tag"
                  size="sm"
                  color="primary"
                  text-color="grey-5"
                  class="q-ma-xs"
                />
                <q-chip
                  v-if="(assistant.configuration.tags as string[]).length > 3"
                  :label="`+${(assistant.configuration.tags as string[]).length - 3}`"
                  size="sm"
                  color="primary"
                  text-color="grey-5"
                  class="q-ma-xs"
                />
              </div>
            </div>
          </q-card-section>

          <q-separator />

          <!-- Action Button -->
          <q-card-section class="col-auto q-pa-md">
            <q-btn
              unelevated
              :color="assistant.avatar_bg_color || 'accent'"
              text-color="white"
              icon="chat"
              :label="$t('startChatting')"
              class="full-width"
              @click.stop="selectAssistant(assistant)"
            />
          </q-card-section>

          <!-- Hover effect overlay -->
          <div class="card-hover-overlay"></div>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { assistantService, type Assistant } from 'src/services/assistantService';

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
 * Gets the number of connected data sources for an assistant
 */
function getConnectorCount(assistant: Assistant): number {
  if (assistant.linked_connectors?.length) {
    return assistant.linked_connectors.length;
  }
  if (assistant.linked_connector_ids?.length) {
    return assistant.linked_connector_ids.length;
  }
  return 0;
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
.assistant-card {
  background: var(--q-secondary);
  border: 1px solid var(--q-third);
  transition: all 0.3s ease;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.assistant-card:hover {
  transform: translateY(-4px);
  border-color: var(--q-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.assistant-card:hover .card-hover-overlay {
  opacity: 1;
}

.card-hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(var(--q-accent-rgb), 0.05) 0%, transparent 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.q-btn {
  border-radius: 8px !important;
}

/* Ensure consistent card height in grid */
.full-height {
  height: 100%;
}
</style>
