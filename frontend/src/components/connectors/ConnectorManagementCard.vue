<template>
  <q-card
    flat
    class="connector-management-card bg-primary column full-height clickable"
    @click="$emit('edit')"
  >
    <!-- Banner Section -->
    <div class="connector-card-banner">
      <!-- Background Glow based on Provider -->
      <div class="glow-overlay" :style="glowStyle"></div>

      <!-- Provider Pill (Top Right) -->
      <div class="provider-pill-header" :style="pillStyle">
        <q-img
          v-if="providerLogo"
          :src="providerLogo"
          width="12px"
          height="12px"
          class="q-mr-xs provider-logo"
          fit="contain"
        />
        <q-icon v-else name="bolt" size="12px" class="q-mr-xs" />
        {{ providerLabel }}
      </div>
    </div>

    <!-- Info Section -->
    <q-card-section class="q-pt-none q-px-lg relative-position info-section flex-grow">
      <!-- Overlapping Avatar (Type Icon) -->
      <div class="avatar-wrapper">
        <div class="avatar-ring" :style="{ borderColor: typeColor }">
          <q-avatar size="80px" class="connector-avatar-main shadow-5" :color="typeBgColor">
            <q-icon :name="typeIcon" size="40px" :style="{ color: typeColor }" />
          </q-avatar>
        </div>
        <!-- Status Dot -->
        <div
          class="status-dot shadow-2"
          :class="{
            'status-dot--active': isSyncing,
            'status-dot--error': connector.status === ConnectorStatus.ERROR,
            'status-dot--idle': connector.status === ConnectorStatus.IDLE || connector.status === ConnectorStatus.PAUSED,
            'status-dot--queued': connector.status === ConnectorStatus.QUEUED
          }"
        >
          <q-tooltip>{{ $t(connector.status) }}</q-tooltip>
        </div>
      </div>

      <!-- Identification -->
      <div class="column q-mt-sm">
        <div class="row no-wrap items-center justify-between">
          <div class="text-h6 text-weight-bolder connector-name ellipsis">
            {{ connector.name }}
          </div>
          <!-- Enable Toggle -->
          <q-toggle
            :model-value="connector.is_enabled"
            @update:model-value="(val) => $emit('toggle', val)"
            dense
            size="xs"
            color="positive"
            class="q-ml-sm"
            @click.stop
          >
             <AppTooltip>{{ connector.is_enabled ? $t('enabled') : $t('disabled') }}</AppTooltip>
          </q-toggle>
        </div>

        <!-- Description -->
        <div class="description-text q-mb-md">
          {{ connector.description || $t('noDescription') }}
          <AppTooltip v-if="connector.description && connector.description.length > 50">
            {{ connector.description }}
          </AppTooltip>
        </div>

        <!-- ACL Tags -->
        <div v-if="aclTags.length > 0" class="row q-gutter-xs q-mb-md">
          <q-chip
            v-for="tag in aclTags"
            :key="tag"
            size="xs"
            color="accent"
            text-color="grey-3"
            class="q-ma-none"
          >
            {{ tag }}
          </q-chip>
        </div>

        <!-- Metrics & Schedule -->
        <div class="metrics-grid q-mb-md">
          <div class="metric-item">
            <q-icon name="description" size="14px" class="q-mr-xs" />
            <span class="metric-value">{{ connector.total_docs_count || 0 }}</span>
            <span class="metric-label q-ml-xs">{{ $t('documents') }}</span>
          </div>
          <div class="metric-item">
            <q-icon name="schedule" size="14px" class="q-mr-xs" />
            <span class="metric-label">{{ scheduleLabel }}</span>
          </div>
          <div class="metric-item full-width">
             <q-icon name="history" size="14px" class="q-mr-xs" />
             <span class="metric-label">{{ $t('lastSync') }}:</span>
             <span class="metric-value q-ml-xs">{{ lastSyncDate || $t('neverSynced') }}</span>
          </div>
        </div>

        <!-- Sync Progress (Visible when index/vectoring) -->
        <div v-if="isSyncing" class="progress-section q-mb-sm">
          <q-linear-progress
            :value="progressValue"
            rounded
            size="8px"
            color="positive"
            track-color="transparent"
            class="q-mb-xs"
          />
          <div class="row justify-between text-caption text-grey-5" style="font-size: 10px;">
            <span>{{ progressLabel }}</span>
            <span>{{ Math.round(progressValue * 100) }}%</span>
          </div>
        </div>

        <!-- Error message if any -->
        <div v-if="connector.status === ConnectorStatus.ERROR && connector.last_error" class="error-strip q-mt-xs pointer" @click.stop="$emit('show-error')">
           <q-icon name="error" color="negative" size="xs" class="q-mr-xs" />
           <span class="text-negative ellipsis" style="font-size: 11px;">{{ connector.last_error }}</span>
        </div>
      </div>
    </q-card-section>

    <!-- Card Actions Footer -->
    <q-card-actions align="around" class="q-pb-md q-px-md actions-footer">
      <!-- Documents Listing -->
      <q-btn flat round dense icon="playlist_add" size="sm" class="action-btn" @click.stop="$emit('view-docs')">
        <AppTooltip>{{ $t('viewDocuments') }}</AppTooltip>
      </q-btn>

      <!-- Sync / Stop Sync -->
      <q-btn
        flat
        round
        dense
        :icon="isSyncing ? 'stop' : 'play_arrow'"
        :color="isSyncing ? 'warning' : 'grey-5'"
        size="sm"
        class="action-btn"
        :disable="!connector.is_enabled"
        @click.stop="$emit('sync')"
      >
        <AppTooltip>{{ isSyncing ? $t('stopSync') : $t('syncNow') }}</AppTooltip>
      </q-btn>

      <!-- Refresh Scan (for folders) -->
      <q-btn
        v-if="connector.connector_type === ConnectorType.LOCAL_FOLDER"
        flat
        round
        dense
        icon="sync"
        color="positive"
        size="sm"
        class="action-btn"
        @click.stop="$emit('refresh')"
      >
        <AppTooltip>{{ $t('refreshFiles') }}</AppTooltip>
      </q-btn>

      <!-- Delete -->
      <q-btn flat round dense icon="delete" color="negative" size="sm" class="action-btn" @click.stop="$emit('delete')">
        <AppTooltip>{{ $t('delete') }}</AppTooltip>
      </q-btn>
    </q-card-actions>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { date } from 'quasar';
import { type Connector, getScheduleLabel } from 'src/models/Connector';
import { ConnectorStatus, ConnectorType } from 'src/models/enums';
import { useAiProviders } from 'src/composables/useAiProviders';
import AppTooltip from 'components/common/AppTooltip.vue';

const props = defineProps<{
  connector: Connector;
}>();

defineEmits(['edit', 'delete', 'sync', 'refresh', 'view-docs', 'toggle', 'show-error']);

const { t } = useI18n();
const { getProviderLogo, getProviderColor } = useAiProviders();

// --- PROVIDER INFO ---
const providerLabel = computed(() => {
  const p = props.connector.configuration?.ai_provider || 'gemini';
  return t(p.toLowerCase());
});

const providerLogo = computed(() => getProviderLogo(props.connector.configuration?.ai_provider || 'gemini'));
const providerColor = computed(() => getProviderColor(props.connector.configuration?.ai_provider || 'gemini'));

const pillStyle = computed(() => {
  const color = providerColor.value || 'grey-7';
  return {
    backgroundColor: `rgba(var(--q-${color}-rgb, 100, 100, 100), 0.12)`,
    backdropFilter: 'blur(8px)',
    border: `1px solid rgba(var(--q-${color}-rgb, 100, 100, 100), 0.25)`,
    color: `var(--q-${color})`
  };
});

const glowStyle = computed(() => {
  const color = providerColor.value || 'grey-7';
  return {
    background: `radial-gradient(circle at 50% 0%, var(--q-${color})15 0%, transparent 70%)`
  };
});

// --- TYPE INFO ---
const typeIcon = computed(() => {
  switch (props.connector.connector_type) {
    case ConnectorType.LOCAL_FILE: return 'file_upload';
    case ConnectorType.LOCAL_FOLDER: return 'folder';
    case ConnectorType.SQL: return 'storage';
    case ConnectorType.WEB: return 'language';
    case ConnectorType.CONFLUENCE: return 'description';
    case ConnectorType.SHAREPOINT: return 'cloud';
    default: return 'hub';
  }
});

const typeColor = computed(() => {
  switch (props.connector.connector_type) {
    case ConnectorType.LOCAL_FOLDER: return 'var(--q-warning)';
    case ConnectorType.SQL: return 'var(--q-info)';
    case ConnectorType.WEB: return 'var(--q-accent)';
    default: return 'var(--q-grey-5)';
  }
});

const typeBgColor = computed(() => {
  switch (props.connector.connector_type) {
    case ConnectorType.LOCAL_FOLDER: return 'amber-2';
    case ConnectorType.SQL: return 'blue-2';
    case ConnectorType.WEB: return 'purple-2';
    default: return 'grey-9';
  }
});

// --- CONTENT ---
const aclTags = computed(() => props.connector.configuration?.connector_acl || []);

const scheduleLabel = computed(() => {
  if (props.connector.schedule_type === 'manual') return t('scheduleManual');
  return getScheduleLabel(props.connector.schedule_cron, t);
});

const lastSyncDate = computed(() => {
  if (!props.connector.last_vectorized_at) return null;
  return date.formatDate(props.connector.last_vectorized_at, 'DD/MM/YYYY HH:mm');
});

// --- STATUS & PROGRESS ---
const isSyncing = computed(() => {
  return props.connector.status === ConnectorStatus.SYNCING || 
         props.connector.status === ConnectorStatus.VECTORIZING;
});

const progressValue = computed(() => {
  if (props.connector.sync_total && props.connector.sync_total > 0) {
    return (props.connector.sync_current || 0) / props.connector.sync_total;
  }
  if (props.connector.total_docs_count > 0) {
    return props.connector.indexed_docs_count / props.connector.total_docs_count;
  }
  return 0;
});

const progressLabel = computed(() => {
  const current = props.connector.sync_total ? props.connector.sync_current : props.connector.indexed_docs_count;
  const total = props.connector.sync_total ? props.connector.sync_total : props.connector.total_docs_count;
  return `${current} / ${total}`;
});
</script>

<style scoped>
.connector-management-card {
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.connector-management-card:hover {
  transform: translateY(-8px);
  border-color: var(--q-sixth);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.connector-card-banner {
  height: 80px;
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.glow-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  pointer-events: none;
  opacity: 0.6;
  transition: opacity 0.4s ease;
}

.connector-management-card:hover .glow-overlay {
  opacity: 0.8;
}

.provider-pill-header {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  z-index: 5;
}

.avatar-wrapper {
  margin-top: -40px;
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}

.avatar-ring {
  padding: 4px;
  border: 2px solid;
  border-radius: 50%;
  transition: all 0.4s ease;
  background: var(--q-primary);
}

.connector-management-card:hover .avatar-ring {
  transform: scale(1.05) rotate(2deg);
}

.status-dot {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--q-primary);
  z-index: 2;
  transition: all 0.3s ease;
}

.status-dot--active {
  background: #00e676;
  box-shadow: 0 0 10px rgba(0, 230, 118, 0.4);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
}

.status-dot--error { background: var(--q-negative); }
.status-dot--idle { background: #757575; }
.status-dot--queued { background: var(--q-warning); }

.connector-name {
  letter-spacing: -0.01em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  line-height: 1.1;
  max-width: 80%;
}

.description-text {
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--q-text-sub);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  opacity: 0.5;
  min-height: 38px;
}

.metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-item {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.75rem;
  color: var(--q-text-sub);
}

.metric-item.full-width {
  width: 100%;
}

.metric-value {
  font-weight: 700;
  color: var(--q-text-main);
}

.metric-label {
  opacity: 0.7;
}

.error-strip {
  background: rgba(var(--q-negative-rgb), 0.1);
  padding: 4px 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
}

.actions-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.03);
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
}

.action-btn {
  transition: all 0.3s ease;
}

.action-btn:hover {
  transform: scale(1.1);
  background: rgba(255, 255, 255, 0.05);
}
</style>
