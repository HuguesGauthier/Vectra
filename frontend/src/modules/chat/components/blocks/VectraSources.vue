<template>
  <q-expansion-item
    class="sources-block q-my-sm"
    header-class="header-bg"
    expand-icon="arrow_drop_down"
    :expand-icon-class="`custom-chevron-${textColor.replace('#', '')}`"
    :style="{ color: textColor }"
  >
    <template v-slot:header>
      <div class="row items-center full-width">
        <q-icon name="description" size="xs" class="q-mr-sm" :style="{ color: textColor }" />
        <div class="text-subtitle2 text-weight-bold flex-1" :style="{ color: textColor }">
          {{ $t('sources') || 'Sources' }}
        </div>
        <div class="text-caption q-ml-sm" :style="{ color: textColor, opacity: 0.8 }">
          ({{ totalSources }} {{ $t('from') }} {{ fileCount }}
          {{ fileCount === 1 ? $t('file') : $t('files') }})
        </div>
      </div>
    </template>

    <q-card class="transparent-bg shadow-none">
      <q-card-section class="q-pt-none">
        <div
          v-for="(group, key) in groupedSources"
          :key="key"
          class="source-group q-mb-sm q-pa-sm border-rounded-8"
          :class="{ 'audio-source': group.isAudio, 'text-source': !group.isAudio }"
        >
          <!-- Group Header -->
          <div class="row items-center q-mb-sm wrap">
            <q-icon
              :name="group.isAudio ? 'audiotrack' : 'insert_drive_file'"
              :style="{ color: textColor }"
              class="q-mr-sm"
              size="20px"
            />
            <span
              class="text-weight-medium text-body2 q-mr-sm ellipsis style-file-name"
              :title="group.fileName"
            >
              {{ group.fileName }}
            </span>
            <q-chip
              dense
              :style="{ backgroundColor: `${textColor}26`, color: textColor }"
              class="q-px-sm text-caption text-weight-medium"
            >
              {{ group.items.length }}
              {{ group.items.length === 1 ? $t('excerpt') : $t('excerpts') }}
            </q-chip>

            <q-space />

            <q-btn
              v-if="group.documentId"
              flat
              dense
              no-caps
              icon-right="open_in_new"
              :label="$t('openFile') || 'Open File'"
              class="open-file-btn text-caption q-px-sm"
              :style="{
                backgroundColor: `${textColor}26`,
                border: `1px solid ${textColor}66`,
                color: textColor,
              }"
              @click="openFile(group.documentId)"
            />
          </div>

          <!-- Items -->
          <div class="source-items column gap-sm q-pl-sm">
            <div
              v-for="(source, sIdx) in group.items"
              :key="`src-${sIdx}`"
              class="source-item q-pa-sm border-rounded-4 relative-position"
            >
              <!-- Audio Player -->
              <template v-if="group.isAudio">
                <div class="text-caption text-purple-3 q-mb-xs row items-center">
                  <q-icon name="timer" size="xs" class="q-mr-xs" :style="{ color: textColor }" />
                  <span :style="{ color: textColor }">{{
                    source.metadata?.timestamp_start || '00:00'
                  }}</span>
                </div>
                <audio
                  v-if="getAudioUrl(source)"
                  controls
                  :src="getAudioUrl(source)"
                  class="full-width"
                  style="height: 32px"
                ></audio>
                <div v-else class="text-negative text-italic text-caption">Audio unavailable</div>
              </template>

              <!-- Text Content -->
              <template v-else>
                <div
                  v-if="getPageLabel(source)"
                  class="text-caption q-mb-xs text-weight-medium"
                  :style="{ color: textColor, opacity: 0.9 }"
                >
                  {{ $t('page') }} {{ getPageLabel(source) }}
                </div>
                <div class="source-content text-caption" :style="{ color: textColor, opacity: 0.8 }">
                  {{ truncateContent(source.content, 200) }}
                </div>
              </template>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { api } from 'boot/axios';
import type { Source } from 'src/stores/publicChatStore';

const props = defineProps<{
  sources: Source[];
  textColor: string;
}>();

const totalSources = computed(() => props.sources.length);

const groupedSources = computed(() => {
  const groups: Record<
    string,
    { fileName: string; documentId?: string; isAudio: boolean; items: Source[] }
  > = {};

  props.sources.forEach((source) => {
    const meta = source.metadata || {};
    const fileNameRaw = meta.file_name || meta.filename || meta.name || source.name;
    const fileName = typeof fileNameRaw === 'string' ? fileNameRaw : 'Unknown';
    const docIdRaw = meta.connector_document_id;
    const documentId =
      typeof docIdRaw === 'string' || typeof docIdRaw === 'number' ? String(docIdRaw) : undefined;
    const key: string = documentId || fileName;
    const isAudio = source.type === 'audio' || meta.connector_type === 'audio';

    if (!groups[key]) {
      const newGroup: { fileName: string; documentId?: string; isAudio: boolean; items: Source[] } =
        {
          fileName,
          isAudio,
          items: [],
        };
      if (documentId) {
        newGroup.documentId = documentId;
      }
      groups[key] = newGroup;
    }
    const group = groups[key];
    if (group) {
      group.items.push(source);
    }
  });

  return groups;
});

const fileCount = computed(() => Object.keys(groupedSources.value).length);

const openFile = (documentId: string) => {
  window.dispatchEvent(new CustomEvent('vectra-open-file', { detail: documentId }));
};

const getAudioUrl = (source: Source) => {
  const rawId = source.metadata?.connector_document_id;
  const fileId = typeof rawId === 'string' || typeof rawId === 'number' ? String(rawId) : '';
  if (!fileId) return '';
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api/v1';
  return `${baseUrl.replace(/\/$/, '')}/audio/stream/${fileId}`;
};

const getPageLabel = (source: Source) => {
  return source.metadata?.page_label || source.metadata?.page_number || source.metadata?.page || '';
};

const truncateContent = (content?: string, length = 150) => {
  if (!content) return '';
  if (content.length <= length) return content;
  return content.substring(0, length) + '...';
};
</script>

<style scoped>
.sources-block {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.05);
}

.header-bg {
  background: transparent;
  border-bottom: 1px solid v-bind('`${textColor}26`');
}

.transparent-bg {
  background: transparent !important;
}

.source-group {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid v-bind('`${textColor}33`');
  border-left: 4px solid v-bind('textColor');
}

/* Removed hardcoded color overrides to maintain full theme consistency as requested */

.bg-opacity-2 {
  background: rgba(255, 255, 255, 0.1) !important;
}

.style-file-name {
  max-width: 250px;
  word-break: break-all;
}

.open-file-btn {
  border-radius: 8px;
  transition: all 0.2s ease;
}
.open-file-btn:hover {
  filter: brightness(1.2);
}

.gap-sm {
  gap: 8px;
}

.source-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid v-bind('`${textColor}1A`');
  border-left: 3px solid v-bind('`${textColor}66`');
}
.text-source .source-item {
  border-left-color: v-bind('`${textColor}80`');
}
.audio-source .source-item {
  border: 1px solid v-bind('`${textColor}4D`');
  border-left: 3px solid v-bind('`${textColor}99`');
  background: rgba(255, 255, 255, 0.08);
}

::v-deep(.q-expansion-item__toggle-icon) {
  color: v-bind('textColor') !important;
}

.source-content {
  line-height: 1.4;
}
</style>
