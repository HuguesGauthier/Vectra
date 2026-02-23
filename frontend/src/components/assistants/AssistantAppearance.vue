<template>
  <q-card class="column bg-primary q-pa-md">
    <!-- Row 1: Avatar and Upload -->
    <div class="row q-col-gutter-lg">
      <!-- Left: Avatar -->
      <div class="col-12 col-md-4 row items-center justify-center">
        <div class="column items-center justify-start q-pt-md">
          <!-- Draggable Avatar Container -->
          <div class="avatar-wrapper relative-position q-mb-md">
            <div
              class="avatar-container"
              @mousedown="startDrag"
              @touchstart.passive="startDrag"
              :class="{ 'cursor-grab': !isDragging, 'cursor-grabbing': isDragging }"
            >
              <q-avatar :style="avatarStyle" size="120px" class="shadow-10">
                <img
                  v-if="avatarUrl"
                  :src="avatarUrl"
                  class="avatar-image"
                  :style="{ objectPosition: `center ${localAvatarPositionY ?? 50}%` }"
                />
                <q-icon v-else name="psychology" size="60px" />
              </q-avatar>

              <!-- Overlay Hint (Always visible on hover or dragging) -->
              <div v-if="avatarUrl" class="drag-hint">
                <q-icon name="open_with" size="24px" color="white" style="opacity: 0.9" />
              </div>
            </div>

            <!-- Vertical Position Slider Indicator (Visual Aid) -->
            <div
              v-if="avatarUrl"
              class="absolute-right full-height flex flex-center"
              :style="{
                right: '-20px',
                opacity: isDragging ? 1 : 0,
                transition: 'opacity 0.2s ease',
              }"
            >
              <div
                class="rounded-borders"
                style="
                  width: 4px;
                  height: 100px;
                  position: relative;
                  overflow: hidden;
                  background-color: var(--q-third);
                "
              >
                <div
                  class="bg-accent absolute-top full-width"
                  :style="{
                    height: '20%',
                    top: `${localAvatarPositionY * 0.8}%`,
                    transition: 'none',
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Upload -->
      <div class="col-12 col-md-7 row items-center justify-left">
        <!-- 1. Avatar Upload -->
        <div class="q-pt-md">
          <div class="text-subtitle2 q-mb-sm flex items-center">
            <q-icon name="image" class="q-mr-xs" size="xs" />
            {{ $t('avatarImage') }}
          </div>
          <div class="row q-gutter-sm">
            <q-file
              v-model="avatarFile"
              accept="image/*"
              @update:model-value="handleFileUpload"
              max-file-size="2097152"
              dense
              borderless
              style="border: 1px solid var(--q-sixth); border-radius: 8px"
              class="col-grow"
              bg-color="secondary"
              :label="$t('uploadPhoto')"
            >
              <template v-slot:prepend>
                <q-icon name="photo_camera" color="accent" class="q-pa-xs" />
              </template>
            </q-file>
            <q-btn v-if="hasAvatar" outline color="negative" icon="delete" @click="deleteAvatar">
              <q-tooltip>{{ $t('removePhoto') }}</q-tooltip>
            </q-btn>
          </div>
          <div class="text-caption q-mt-xs">
            {{ hasAvatar ? $t('dragToPosition') : $t('uploadAvatarHint') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Full Width Separator -->
    <div class="full-width q-px-md">
      <div style="height: 1px; background-color: var(--q-fourth)" class="q-my-lg"></div>
    </div>

    <!-- Row 2: Chat Bubble and Appearance -->
    <div class="row q-col-gutter-lg row items-center">
      <!-- Left: Separator and Preview -->
      <div class="col-12 col-md-4">
        <div class="column items-center full-width">
          <!-- Chat Bubble Preview -->
          <div class="chat-preview q-pa-md rounded-borders shadow-2" :style="previewBubbleStyle">
            <div style="font-size: 0.95rem; line-height: 1.4">
              {{
                $t('previewMessage') || "Hello! I'm your AI assistant. How can I help you today?"
              }}
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Appearance and Presets -->
      <div class="col-12 col-md-7">
        <div class="column q-gutter-y-lg">
          <!-- 2. Colors -->
          <div>
            <div class="text-subtitle2 q-mb-sm flex items-center">
              <q-icon name="palette" class="q-mr-xs" size="xs" />
              {{ $t('appearance') }}
            </div>

            <div class="row q-col-gutter-md">
              <!-- Background -->
              <div class="col-6">
                <div
                  class="bg-secondary rounded-borders q-pa-sm row items-center justify-between border-subtle"
                  style="border: 1px solid var(--q-sixth); border-radius: 8px"
                >
                  <div class="row items-center q-gutter-x-sm">
                    <div
                      class="color-circle shadow-3"
                      :style="{ backgroundColor: bgColor || 'var(--q-primary)' }"
                    ></div>
                    <div class="text-caption">{{ $t('background') }}</div>
                  </div>
                  <q-btn flat round size="sm" icon="edit" color="grey-5">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-color
                        :model-value="bgColor"
                        @update:model-value="$emit('update:bgColor', $event || '')"
                        default-view="palette"
                        format-model="hex"
                        no-header-tabs
                        dark
                        class="bg-dark shadow-10"
                      />
                    </q-popup-proxy>
                  </q-btn>
                </div>
              </div>

              <!-- Text Color -->
              <div class="col-6">
                <div
                  class="bg-secondary rounded-borders q-pa-sm row items-center justify-between border-subtle"
                  style="border: 1px solid var(--q-sixth); border-radius: 8px"
                >
                  <div class="row items-center q-gutter-x-sm">
                    <div
                      class="color-circle shadow-3 flex flex-center"
                      :style="{ backgroundColor: textColor || 'white' }"
                    >
                      <span class="text-xs text-bold" :style="{ color: bgColor || 'black' }"
                        >Aa</span
                      >
                    </div>
                    <div class="text-caption">{{ $t('text') }}</div>
                  </div>
                  <q-btn flat round size="sm" icon="edit" color="grey-5">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-color
                        :model-value="textColor"
                        @update:model-value="$emit('update:textColor', $event || '')"
                        default-view="palette"
                        format-model="hex"
                        no-header-tabs
                        dark
                        class="bg-dark shadow-10"
                      />
                    </q-popup-proxy>
                  </q-btn>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Presets -->
          <div>
            <div class="row items-center justify-between q-mb-sm">
              <div class="text-subtitle2 flex items-center">
                <q-icon name="style" class="q-mr-xs" size="xs" />
                {{ $t('presets') }}
              </div>
            </div>

            <div class="row q-gutter-sm">
              <div
                v-for="preset in uniquePresets.slice(0, 7)"
                :key="preset.bg"
                class="preset-circle shadow-2 cursor-pointer border-none"
                :style="{ backgroundColor: preset.bg, color: preset.text }"
                @click="applyPreset(preset)"
              >
                <q-icon name="psychology" size="14px" />
                <q-tooltip class="bg-dark text-caption">{{ preset.name }}</q-tooltip>
              </div>
              <div
                class="preset-circle shadow-2 cursor-pointer border-subtle bg-transparent text-grey-5 flex flex-center"
                @click="showPresetsDialog = true"
              >
                <q-icon name="add" size="16px" />
                <q-tooltip class="bg-dark text-caption">{{ $t('viewAll') }}</q-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </q-card>

  <!-- Presets Dialog -->
  <q-dialog v-model="showPresetsDialog" backdrop-filter="blur(4px)">
    <q-card
      class="bg-dark text-white"
      style="width: 800px; max-width: 90vw; border: 1px solid rgba(255, 255, 255, 0.1)"
    >
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ $t('presetLibrary') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class="q-pa-md">
        <div v-for="category in presetCategories" :key="category" class="q-mb-md">
          <div
            class="text-subtitle2 text-grey-5 q-mb-sm uppercase tracking-wide"
            style="font-size: 0.75rem; letter-spacing: 1px"
          >
            {{ category }}
          </div>
          <div class="row q-col-gutter-sm">
            <div
              v-for="preset in getPresetsByCategory(category)"
              :key="preset.name"
              class="col-6 col-sm-4 col-md-3"
            >
              <div
                class="cursor-pointer rounded-borders q-pa-sm relative-position border-subtle transition-all hover-scale"
                :style="{ backgroundColor: preset.bg }"
                @click="
                  applyPreset(preset);
                  showPresetsDialog = false;
                "
              >
                <div class="row items-center q-gutter-x-md">
                  <div
                    class="flex flex-center rounded-borders"
                    :style="{
                      color: preset.text,
                      backgroundColor: 'rgba(255,255,255,0.1)',
                      width: '32px',
                      height: '32px',
                    }"
                  >
                    <q-icon name="psychology" size="18px" />
                  </div>
                  <div class="column">
                    <div
                      class="text-weight-bold"
                      :style="{ color: preset.text, fontSize: '0.85rem' }"
                    >
                      {{ preset.name }}
                    </div>
                    <div :style="{ color: preset.text, opacity: 0.7, fontSize: '0.7rem' }">
                      {{ preset.bg }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { assistantService } from 'src/services/assistantService';

const props = defineProps<{
  name?: string;
  bgColor?: string;
  textColor?: string;
  assistantId?: string | undefined;
  avatarImage?: string | null | undefined; // Filename or null
  avatarPositionY?: number | undefined;
}>();

const emit = defineEmits<{
  (e: 'update:bgColor', val: string): void;
  (e: 'update:textColor', val: string): void;
  (e: 'update:avatarPositionY', val: number): void;
  (e: 'avatar-updated', val: string | null): void;
  (e: 'file-selected', val: File | null): void;
}>();

const { t } = useI18n();
const $q = useQuasar();
const avatarFile = ref<File | null>(null);
const avatarRefreshKey = ref(0);

// Local state for smooth dragging
const localAvatarPositionY = ref(50);

const localAvatarUrl = ref<string | null>(null);

const hasAvatar = computed(() => !!props.avatarImage || !!localAvatarUrl.value);
const blobAvatarUrl = ref<string | null>(null);

const avatarUrl = computed(() => {
  if (localAvatarUrl.value) return localAvatarUrl.value;
  return blobAvatarUrl.value;
});

// Watcher to fetch blob from backend
watch(
  [() => props.assistantId, () => props.avatarImage, avatarRefreshKey],
  async ([newId, newImage]) => {
    // 1. Revoke old URL
    if (blobAvatarUrl.value) {
      URL.revokeObjectURL(blobAvatarUrl.value);
      blobAvatarUrl.value = null;
    }

    // 2. Fetch new
    if (newId && newImage) {
      try {
        const blob = await assistantService.getAvatarBlob(newId);
        blobAvatarUrl.value = URL.createObjectURL(blob);
      } catch (e) {
        console.error('Failed to load avatar blob', e);
        blobAvatarUrl.value = null;
      }
    }
  },
  { immediate: true },
);

// Drag to position avatar
const isDragging = ref(false);
let startY = 0;
let startPosition = 50;

// Sync local state with prop
watch(
  () => props.avatarPositionY,
  (val) => {
    if (!isDragging.value) {
      localAvatarPositionY.value = val ?? 50;
    }
  },
  { immediate: true },
);

async function handleFileUpload(file: File | null) {
  if (!file) {
    if (localAvatarUrl.value) {
      URL.revokeObjectURL(localAvatarUrl.value);
      localAvatarUrl.value = null;
    }
    return;
  }

  // Case 1: Existing Assistant -> Direct Upload
  if (props.assistantId) {
    try {
      const updatedAssistant = await assistantService.uploadAvatar(props.assistantId, file);
      emit('avatar-updated', updatedAssistant.avatar_image || null);
      avatarRefreshKey.value++; // Force refresh
      avatarFile.value = null; // Reset input
      $q.notify({
        type: 'positive',
        message: t('avatarUploaded'),
      });
    } catch {
      $q.notify({
        type: 'negative',
        message: t('avatarUploadFailed'),
      });
      avatarFile.value = null;
    }
  }
  // Case 2: New Assistant -> Local Preview & Emit
  else {
    if (localAvatarUrl.value) {
      URL.revokeObjectURL(localAvatarUrl.value);
    }
    localAvatarUrl.value = URL.createObjectURL(file);
    emit('file-selected', file);
  }
}

async function deleteAvatar() {
  if (props.assistantId) {
    try {
      await assistantService.deleteAvatar(props.assistantId);
      emit('avatar-updated', null);
      avatarRefreshKey.value++; // Force refresh
      $q.notify({
        type: 'positive',
        message: t('avatarRemoved'),
      });
    } catch {
      $q.notify({
        type: 'negative',
        message: t('avatarRemoveFailed'),
      });
    }
  } else {
    if (localAvatarUrl.value) {
      URL.revokeObjectURL(localAvatarUrl.value);
      localAvatarUrl.value = null;
    }
    emit('file-selected', null);
  }

  // Reset UI
  avatarFile.value = null;
  emit('update:avatarPositionY', 50);
}

import { assistantPresets } from './assistantPresets';

const showPresetsDialog = ref(false);

const uniquePresets = computed(() => {
  // Return just the first 7 diverse presets for the inline view
  return assistantPresets
    .filter((p) => p.category === 'Popular' || p.category === 'Vibrant')
    .slice(0, 7);
});

const presetCategories = computed(() => {
  return [...new Set(assistantPresets.map((p) => p.category))];
});

function getPresetsByCategory(category: string) {
  return assistantPresets.filter((p) => p.category === category);
}

const avatarStyle = computed(() => {
  const style: Record<string, string> = {
    color: props.textColor || 'white', // Default text color
  };

  if (props.bgColor) {
    if (props.bgColor.startsWith('#') || props.bgColor.startsWith('rgb')) {
      style.backgroundColor = props.bgColor;
    } else {
      style.backgroundColor = props.bgColor;
    }
  } else {
    // Default background if none selected, matches q-primary usually or defined default
    style.backgroundColor = 'var(--q-primary)';
  }

  return style;
});

function applyPreset(preset: { bg: string; text: string }) {
  emit('update:bgColor', preset.bg);
  emit('update:textColor', preset.text);
}

const previewBubbleStyle = computed(() => {
  return {
    backgroundColor: props.bgColor || 'var(--q-primary)',
    color: props.textColor || 'white',
    borderTopLeftRadius: '12px',
    borderTopRightRadius: '12px',
    borderBottomRightRadius: '12px',
    borderBottomLeftRadius: '0px',
    maxWidth: '120px',
    textAlign: 'left' as const,
    lineHeight: '1.2',
  };
});
// Drag to position avatar

function startDrag(e: MouseEvent | TouchEvent) {
  if (!hasAvatar.value) return;

  isDragging.value = true;
  startY = 'touches' in e && e.touches[0] ? e.touches[0].clientY : (e as MouseEvent).clientY;
  startPosition = localAvatarPositionY.value;

  // Add event listeners
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.addEventListener('touchmove', onDrag);
  document.addEventListener('touchend', stopDrag);

  // e.preventDefault();
}

function onDrag(e: MouseEvent | TouchEvent) {
  if (!isDragging.value) return;

  const currentY =
    'touches' in e && e.touches[0] ? e.touches[0].clientY : (e as MouseEvent).clientY;
  const deltaY = currentY - startY;

  // Convert pixels to percentage (100px avatar height) based on UserFormDialog logic
  const deltaPercent = (deltaY / 100) * 100;

  // Update position (inverted: drag down = move image up in view)
  let newPosition = startPosition - deltaPercent;
  newPosition = Math.max(0, Math.min(100, newPosition));

  // Sync to UserFormDialog: round the value
  localAvatarPositionY.value = Math.round(newPosition);
}

function stopDrag() {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('touchmove', onDrag);
  document.removeEventListener('touchend', stopDrag);

  // Commit the final position
  emit('update:avatarPositionY', localAvatarPositionY.value);
}

onUnmounted(() => {
  stopDrag();

  if (blobAvatarUrl.value) {
    URL.revokeObjectURL(blobAvatarUrl.value);
  }
  if (localAvatarUrl.value) {
    URL.revokeObjectURL(localAvatarUrl.value);
  }
});
</script>

<style scoped>
.color-indicator {
  border: 2px solid rgba(255, 255, 255, 0.1);
  transition: transform 0.2s ease;
}

.color-indicator:active {
  transform: scale(0.95);
}

/* New Styles for Redesign */
.border-subtle {
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.preset-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.preset-circle:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.color-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
  user-select: none;
}

.avatar-container {
  position: relative;
  display: inline-block;
  /* border-radius removed logic handled by q-avatar mask, container is square for drag zone */
  cursor: grab;
  transition: transform 0.1s;
  touch-action: none;
}

.avatar-container:active {
  cursor: grabbing;
  transform: scale(0.98);
}

.drag-hint {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%; /* Match avatar shape */
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.avatar-container:hover .drag-hint,
.avatar-container.cursor-grabbing .drag-hint {
  opacity: 1;
}

.chat-preview {
  position: relative;
  max-width: 85%;
  border-bottom-left-radius: 0; /* Chat bubble tail effect */
}
</style>
