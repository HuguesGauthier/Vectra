<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Main Dashboard Stats (Real-time) -->
    <div class="dashboard-home-container q-pb-md q-pl-none q-mb-md">
      <!-- Hero Header -->

      <!-- Loading State -->
      <div v-if="!dashboardStore.stats" class="loading-state">
        <q-spinner-grid color="primary" size="80px" />
        <div class="text-h6 q-mt-lg">{{ t('loadingDashboard') }}...</div>
      </div>

      <div v-else>
        <!-- Pipeline Dashboard Grid -->
        <div class="row q-col-gutter-lg">
          <!-- ========== CONNECT CARD (Blue) ========== -->

          <div class="col-12 col-md-4">
            <q-card flat class="pipeline-card pipeline-card--connect">
              <!-- Background Glow -->
              <div class="glow-overlay glow-overlay--blue"></div>

              <q-card-section>
                <div class="row items-center q-mb-md">
                  <q-icon name="cable" size="32px" color="blue-5" class="q-mr-sm" />
                  <div>
                    <div class="text-h6 text-weight-bold">
                      {{ t('cardConnect').toUpperCase() }}
                    </div>
                    <div class="text-caption text-grey-6">{{ t('dataSources') }}</div>
                  </div>
                </div>

                <!-- Status Badge -->
                <div class="q-mb-md">
                  <q-badge
                    :color="getSystemStatusColor(dashboardStore.stats.connect.system_status)"
                    :label="getSystemStatusLabel(dashboardStore.stats.connect.system_status)"
                    class="status-badge-large"
                  >
                    <q-icon
                      :name="getSystemStatusIcon(dashboardStore.stats.connect.system_status)"
                      size="16px"
                      class="q-ml-xs"
                    />
                  </q-badge>
                </div>

                <!-- Metrics -->
                <div class="metric-group">
                  <div class="metric-item">
                    <div class="metric-label">{{ t('activePipelines') }}</div>
                    <div class="metric-value metric-value--primary text-blue-4">
                      {{ dashboardStore.stats.connect.active_pipelines }}
                      <span class="metric-unit"
                        >/ {{ dashboardStore.stats.connect.total_connectors }}</span
                      >
                    </div>
                  </div>

                  <q-separator dark class="q-my-md" color="blue-4" />

                  <div class="metric-item">
                    <div class="metric-label">{{ t('totalConnectors') }}</div>
                    <div class="metric-value text-blue-4">
                      {{ dashboardStore.stats.connect.total_connectors }}
                    </div>
                  </div>

                  <q-separator dark class="q-my-md" color="blue-4" />

                  <div class="metric-item">
                    <div class="metric-label">
                      <q-icon name="sync" size="16px" class="q-mr-xs" />
                      {{ t('lastSync') }}
                    </div>
                    <div class="metric-value metric-value--small text-blue-4">
                      {{ formatLastSync(dashboardStore.stats.connect.last_sync_time) }}
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- ========== VECTORIZE CARD (Purple) ========== -->
          <div class="col-12 col-md-4">
            <q-card flat class="pipeline-card pipeline-card--vectorize">
              <!-- Background Glow -->
              <div class="glow-overlay glow-overlay--purple"></div>

              <q-card-section>
                <div class="row items-center q-mb-md">
                  <q-icon name="hub" size="32px" color="purple-5" class="q-mr-sm" />
                  <div>
                    <div class="text-h6 text-weight-bold">
                      {{ t('cardVectorize').toUpperCase() }}
                    </div>
                    <div class="text-caption text-grey-6">{{ t('indexing') }}</div>
                  </div>
                </div>

                <!-- Success Rate Progress Bar -->
                <div class="q-mb-md">
                  <div class="row items-center justify-between q-mb-xs">
                    <span class="text-caption">{{ t('successRate') }}</span>
                    <span class="text-caption text-weight-bold">
                      {{ (dashboardStore.stats.vectorize.indexing_success_rate * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <q-linear-progress
                    :value="dashboardStore.stats.vectorize.indexing_success_rate"
                    :color="
                      getSuccessRateColor(dashboardStore.stats.vectorize.indexing_success_rate)
                    "
                    size="8px"
                    rounded
                    class="success-progress"
                  />
                </div>

                <!-- Failed Docs Alert -->
                <q-banner
                  v-if="dashboardStore.stats.vectorize.failed_docs_count > 0"
                  dense
                  class="bg-negative q-mb-md"
                  rounded
                >
                  <template #avatar>
                    <q-icon name="warning" color="white" />
                  </template>
                  {{ dashboardStore.stats.vectorize.failed_docs_count }} {{ t('failedDocs') }}
                </q-banner>

                <!-- Metrics -->
                <div class="metric-group">
                  <div class="metric-item">
                    <div class="metric-label">{{ t('totalVectors') }}</div>
                    <div class="metric-value metric-value--primary text-purple-4">
                      {{ formatLargeNumber(dashboardStore.stats.vectorize.total_vectors) }}
                    </div>
                  </div>

                  <q-separator dark class="q-my-md" color="purple-4" />

                  <div class="metric-item">
                    <div class="metric-label">{{ t('totalTokens') }}</div>
                    <div class="metric-value text-purple-4">
                      {{ formatLargeNumber(dashboardStore.stats.vectorize.total_tokens) }}
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- ========== CHAT CARD (Teal) ========== -->
          <div class="col-12 col-md-4">
            <q-card flat class="pipeline-card pipeline-card--chat">
              <!-- Background Glow -->
              <div class="glow-overlay glow-overlay--teal"></div>

              <q-card-section>
                <div class="row items-center q-mb-md">
                  <q-icon name="forum" size="32px" color="teal-5" class="q-mr-sm" />
                  <div>
                    <div class="text-h6 text-weight-bold">
                      {{ t('cardChat').toUpperCase() }}
                    </div>
                    <div class="text-caption text-grey-6">{{ t('usage30Days') }}</div>
                  </div>
                </div>

                <!-- Average Feedback Score Removed -->

                <!-- Metrics -->
                <div class="metric-group">
                  <div class="metric-item">
                    <div class="metric-label">
                      <q-icon name="groups" size="16px" class="q-mr-xs" />
                      {{ t('sessions') }}
                    </div>
                    <div class="metric-value metric-value--primary text-teal-4">
                      {{ formatLargeNumber(dashboardStore.stats.chat.monthly_sessions) }}
                    </div>
                  </div>

                  <q-separator dark class="q-my-md" color="teal-4" />

                  <div class="metric-item metric-item--critical">
                    <div class="metric-label">
                      <q-icon name="speed" size="16px" class="q-mr-xs text-warning" />
                      {{ t('avgLatency') }} (TTFT)
                    </div>
                    <div class="metric-value metric-value--highlight text-teal-4">
                      {{ dashboardStore.stats.chat.avg_latency_ttft.toFixed(2) }}s
                      <q-chip
                        :color="getLatencyColor(dashboardStore.stats.chat.avg_latency_ttft)"
                        size="sm"
                        text-color="white"
                        class="q-ml-xs"
                      >
                        {{ getLatencyLabel(dashboardStore.stats.chat.avg_latency_ttft) }}
                      </q-chip>
                    </div>
                  </div>

                  <q-separator dark class="q-my-md" color="teal-5" />

                  <div class="metric-item">
                    <div class="metric-label">{{ t('totalTokens') }}</div>
                    <div class="metric-value text-teal-5">
                      {{ formatLargeNumber(dashboardStore.stats.chat.total_tokens_used) }}
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </div>

    <!-- Global Trends Card Removed -->
  </q-page>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDashboardStore } from 'src/stores/dashboardStore';
import { date } from 'quasar';

const { t } = useI18n();
const dashboardStore = useDashboardStore();

// --- REFRESH ---
onMounted(() => {
  void dashboardStore.fetchStats();
});

// ========== COMPUTED PROPERTIES ==========

// ========== UTILITY FUNCTIONS ==========

function formatLastSync(dateString: string | null): string {
  if (!dateString) return t('never');
  const syncDate = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - syncDate.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return t('justNow');
  if (diffMins < 60) return `${diffMins}min ${t('ago')}`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ${t('ago')}`;
  return date.formatDate(syncDate, 'MMM DD, HH:mm');
}

function formatLargeNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
}

function getSystemStatusColor(status: string): string {
  return status === 'ok' ? 'positive' : status === 'degraded' ? 'warning' : 'negative';
}

function getSystemStatusLabel(status: string): string {
  return status === 'ok'
    ? t('healthy')
    : status === 'degraded'
      ? t('statusDegraded').toUpperCase()
      : t('statusError').toUpperCase();
}

function getSystemStatusIcon(status: string): string {
  return status === 'ok' ? 'check_circle' : status === 'degraded' ? 'warning' : 'error';
}

function getSuccessRateColor(rate: number): string {
  if (rate >= 0.9) return 'positive';
  if (rate >= 0.7) return 'warning';
  return 'negative';
}

function getLatencyColor(latency: number): string {
  if (latency < 1.0) return 'positive';
  if (latency < 2.0) return 'warning';
  return 'negative';
}

function getLatencyLabel(latency: number): string {
  if (latency < 1.0) return t('latencyFast').toUpperCase();
  if (latency < 2.0) return t('latencyOk').toUpperCase();
  return t('latencySlow').toUpperCase();
}
</script>

<style lang="scss" scoped>
.dashboard-home-container {
  // Loading State
  .loading-state {
    text-align: center;
    padding: 4rem 0;
  }

  // Pipeline Cards
  .pipeline-card {
    background: linear-gradient(145deg, var(--q-secondary) 0%, rgba(var(--q-secondary-rgb), 0.8) 100%);
    border: 1px solid var(--q-third);
    border-radius: 24px;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    cursor: default;

    &:hover {
      transform: translateY(-8px);
      box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
      border-color: var(--q-sixth);

      .glow-overlay {
        opacity: 0.8;
      }
    }

    .glow-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 150px;
      pointer-events: none;
      opacity: 0.3;
      transition: opacity 0.4s ease;

      &--blue {
        background: radial-gradient(circle at 50% 0%, #42a5f520 0%, transparent 70%);
      }
      &--purple {
        background: radial-gradient(circle at 50% 0%, #ab47bc20 0%, transparent 70%);
      }
      &--teal {
        background: radial-gradient(circle at 50% 0%, #26a69a20 0%, transparent 70%);
      }
    }
  }

  // Status Badge Large
  .status-badge-large {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  // Success Progress Bar
  .success-progress {
    background: rgba(255, 255, 255, 0.05);
    height: 10px !important;
  }

  // Metrics
  .metric-group {
    .metric-item {
      .metric-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        opacity: 0.6;
      }

      .metric-value {
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.02em;

        &--primary {
          font-size: 2.25rem;
        }

        &--small {
          font-size: 1.1rem;
          font-weight: 600;
        }

        &--highlight {
          display: flex;
          align-items: center;
        }

        .metric-unit {
          font-size: 1rem;
          font-weight: 400;
          margin-left: 0.25rem;
          opacity: 0.5;
        }
      }

      &--critical {
        .metric-label {
          color: var(--q-warning);
          opacity: 1;
        }
      }
    }
  }

  // Feedback Highlight
  .feedback-highlight {
    background: var(--q-sixth);
    padding: 1rem;
    border-radius: 16px;
    border: 1px solid var(--q-third);
  }
}
</style>
