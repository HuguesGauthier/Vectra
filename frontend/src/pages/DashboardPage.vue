<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Main Dashboard Stats (Real-time) -->
    <div class="dashboard-home-container q-pb-md q-pl-none q-mb-md">
      <!-- Hero Header -->
      <div class="hero-header q-mb-sm">
        <div class="row items-center justify-between">
          <div>
            <div class="text-h4 text-weight-bold">{{ t('dashboard') }}</div>
            <div class="text-h6 pipeline-subtitle">
              <span class="pipeline-step">{{ t('sloganConnect') }}</span>
              <span class="pipeline-step">{{ t('sloganVectorize') }}</span>
              <span class="pipeline-step">{{ t('sloganChat') }}</span>
            </div>
          </div>

          <!-- Status Indicators Group -->
          <div class="row items-center q-gutter-md">
            <!-- Heartbeat Pills (Admin Only) -->
            <template v-if="authStore.isAdmin">
              <div
                class="status-badge row items-center q-px-md q-py-xs cursor-pointer bg-secondary"
              >
                <div
                  class="live-dot q-mr-sm"
                  :class="apiStatus === 'online' ? 'live-dot--active' : 'bg-negative'"
                ></div>
                <div class="text-caption text-weight-medium">API</div>
                <q-tooltip>{{ apiLatency }}</q-tooltip>
              </div>

              <div class="status-badge bg-secondary row items-center q-px-md q-py-xs">
                <div
                  class="live-dot q-mr-sm"
                  :class="workerStatus === 'online' ? 'live-dot--active' : 'bg-negative'"
                ></div>
                <div class="text-caption text-weight-medium">Worker</div>
              </div>

              <div class="status-badge bg-secondary row items-center q-px-md q-py-xs">
                <div
                  class="live-dot q-mr-sm"
                  :class="storageStatus === 'online' ? 'live-dot--active' : 'bg-negative'"
                ></div>
                <div class="text-caption text-weight-medium">{{ $t('storage') }}</div>
              </div>
            </template>

            <!-- Last Update Badge -->
            <div
              v-if="dashboardStore.stats"
              class="bg-secondary status-badge row items-center q-px-md q-py-xs"
            >
              <div
                class="live-dot q-mr-sm"
                :class="{ 'live-dot--active': dashboardStore.isUpdating }"
              ></div>
              <div class="text-caption text-weight-medium">
                {{ t('lastUpdate') }}: {{ formattedLastUpdate }}
              </div>
            </div>
          </div>
        </div>
      </div>

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
              <div class="card-border-top card-border-top--blue"></div>

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
              <div class="card-border-top card-border-top--purple"></div>

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
              <div class="card-border-top card-border-top--teal"></div>

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
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDashboardStore } from 'src/stores/dashboardStore';
import { useSocketStore } from 'src/stores/socketStore';
import { useAuthStore } from 'src/stores/authStore';
import { date } from 'quasar';

const { t } = useI18n();
const dashboardStore = useDashboardStore();
const socketStore = useSocketStore();
const authStore = useAuthStore();

// --- HEARTBEAT COMPUTED ---
const apiStatus = computed(() => (socketStore.isConnected ? 'online' : 'offline'));
const workerStatus = computed(() => (socketStore.isWorkerOnline ? 'online' : 'offline'));
const storageStatus = computed(() => socketStore.storageStatus);
const apiLatency = computed(() => (socketStore.isConnected ? t('connected') : '--'));

onMounted(() => {
  void dashboardStore.fetchStats();
});

// ========== COMPUTED PROPERTIES ==========

const formattedLastUpdate = computed(() => {
  if (!dashboardStore.lastUpdated) return '';
  const now = Date.now();
  const diff = now - dashboardStore.lastUpdated;
  if (diff < 1000) return t('justNow');
  if (diff < 60000) return Math.floor(diff / 1000) + 's ' + t('ago');
  return date.formatDate(dashboardStore.lastUpdated, 'HH:mm:ss');
});

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
  // Hero Header
  .hero-header {
    padding: 1.5rem 0;

    .pipeline-subtitle {
      font-weight: 300;
      letter-spacing: 2px;

      .pipeline-step {
        margin-right: 1rem;
        opacity: 0.8;
        transition: opacity 0.3s ease;

        &:nth-child(1) {
          color: #42a5f5;
        }
        &:nth-child(2) {
          color: #ab47bc;
        }
        &:nth-child(3) {
          color: #26a69a;
        }

        &:hover {
          opacity: 1;
        }
      }
    }
  }

  // Status Badge
  .status-badge {
    background: rgba(255, 255, 255, 0.05);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #666;
      transition: all 0.3s ease;

      &--active {
        background-color: #00e676;
        box-shadow: 0 0 12px rgba(0, 230, 118, 1);
        animation: pulse-live 1s ease-in-out infinite;
      }
    }
  }

  @keyframes pulse-live {
    0%,
    100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(1.2);
    }
  }

  // Loading State
  .loading-state {
    text-align: center;
    padding: 4rem 0;
  }

  // Pipeline Cards
  .pipeline-card {
    background: linear-gradient(145deg, var(--q-secondary) 0%, var(--q-secondary) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    transition: all 0.3s ease;
    position: relative;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
      border-color: rgba(255, 255, 255, 0.15);
    }

    // Colored top border
    .card-border-top {
      height: 4px;
      width: 100%;

      &--blue {
        background: linear-gradient(90deg, #1976d2 0%, #42a5f5 100%);
      }

      &--purple {
        background: linear-gradient(90deg, #7b1fa2 0%, #ab47bc 100%);
      }

      &--teal {
        background: linear-gradient(90deg, #00897b 0%, #26a69a 100%);
      }
    }
  }

  // Status Badge Large
  .status-badge-large {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.4rem 0.8rem;
    letter-spacing: 1px;
  }

  // Success Progress Bar
  .success-progress {
    background: rgba(255, 255, 255, 0.1);
  }

  // Metrics
  .metric-group {
    .metric-item {
      .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
      }

      .metric-value {
        font-size: 1.5rem;
        font-weight: 700;

        &--primary {
          font-size: 2rem;
        }

        &--small {
          font-size: 1rem;
          font-weight: 500;
        }

        &--highlight {
          display: flex;
          align-items: center;
        }

        .metric-unit {
          font-size: 1rem;
          margin-left: 0.25rem;
        }
      }

      &--critical {
        .metric-label {
          color: #ffa726;
        }
      }
    }
  }

  // Feedback Highlight
  .feedback-highlight {
    background: linear-gradient(135deg, rgba(38, 166, 154, 0.1) 0%, rgba(38, 166, 154, 0.05) 100%);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid rgba(38, 166, 154, 0.2);
  }
}
</style>
