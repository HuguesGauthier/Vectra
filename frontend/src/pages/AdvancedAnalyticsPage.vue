<template>
  <q-page class="bg-primary q-pa-lg">
    <div class="q-pt-md q-pb-sm q-pl-none analytics-container">
      <!-- Loading State -->
      <div v-if="!store.stats" class="loading-state">
        <q-spinner-grid color="primary" size="80px" />
        <div class="text-h6 q-mt-lg">{{ $t('loadingAnalytics') }}...</div>
      </div>

      <!-- KPI Cards Row -->
      <div v-else class="row q-col-gutter-lg q-mb-md">
        <!-- TTFT p95 -->
        <div class="col-12 col-md-3">
          <q-card flat class="pipeline-card pipeline-card--teal">
            <div class="glow-overlay glow-overlay--teal"></div>
            <q-card-section>
              <div class="metric-group">
                <div class="metric-item">
                  <div class="metric-label">
                    <q-icon name="speed" size="16px" class="q-mr-xs" />
                    TTFT (p95)
                  </div>
                  <div class="metric-value metric-value--primary text-teal-4">
                    {{ store.stats?.ttft_percentiles?.p95.toFixed(2) || 'N/A' }}
                    <span class="metric-unit">s</span>
                  </div>
                </div>
                <q-linear-progress
                  :value="getTTFTProgress()"
                  :color="getTTFTColor()"
                  size="6px"
                  rounded
                  class="q-mt-sm performance-progress"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Cache Hit Rate -->
        <div class="col-12 col-md-3">
          <q-card flat class="pipeline-card pipeline-card--purple">
            <div class="glow-overlay glow-overlay--purple"></div>
            <q-card-section>
              <div class="metric-group">
                <div class="metric-item">
                  <div class="metric-label">
                    <q-icon name="storage" size="16px" class="q-mr-xs" />
                    Cache Hit Rate
                  </div>
                  <div class="metric-value metric-value--primary text-purple-4">
                    {{ store.stats?.cache_metrics?.hit_rate.toFixed(1) || '0' }}
                    <span class="metric-unit">%</span>
                  </div>
                  <div class="metric-value metric-value--small q-mt-xs">
                    {{ store.stats?.cache_metrics?.cache_hits || 0 }} /
                    {{ store.stats?.cache_metrics?.total_requests || 0 }} requests
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Daily Cost -->
        <div class="col-12 col-md-3">
          <q-card flat class="pipeline-card pipeline-card--amber">
            <div class="glow-overlay glow-overlay--amber"></div>
            <q-card-section>
              <div class="metric-group">
                <div class="metric-item">
                  <div class="metric-label">
                    <q-icon name="attach_money" size="16px" class="q-mr-xs" />
                    Daily LLM Cost
                  </div>
                  <div class="metric-value metric-value--primary text-amber-4">
                    ${{ totalCost.toFixed(2) }}
                  </div>
                  <div class="metric-value metric-value--small q-mt-xs">
                    {{ totalTokens.toLocaleString() }} tokens
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Reranking Impact -->
        <div class="col-12 col-md-3">
          <q-card flat class="pipeline-card pipeline-card--red">
            <div class="glow-overlay glow-overlay--red"></div>
            <q-card-section>
              <div class="metric-group">
                <div class="metric-item">
                  <div class="metric-label">
                    <q-icon name="compress" size="16px" class="q-mr-xs" />
                    Reranking Impact
                  </div>
                  <div class="metric-value metric-value--primary text-red-4">
                    {{ (store.stats?.reranking_impact?.avg_score_improvement || 0).toFixed(3) }}
                  </div>
                  <div class="metric-value metric-value--small q-mt-xs">
                    from {{ store.stats?.reranking_impact?.reranking_enabled_count || 0 }} sessions
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Charts Row 1 -->
      <div v-if="store.stats" class="row q-col-gutter-lg q-mb-md">
        <!-- Step Breakdown -->
        <div class="col-12 col-md-6">
          <q-card flat class="pipeline-card pipeline-card--purple">
            <div class="glow-overlay glow-overlay--purple"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="timeline" size="28px" color="purple-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">
                  {{ $t('pipelineStepBreakdown') }}
                </div>
              </div>
              <div v-if="store.stats?.step_breakdown.length">
                <div
                  v-for="step in store.stats.step_breakdown"
                  :key="step.step_name"
                  class="q-mb-md"
                >
                  <div class="row items-center justify-between q-mb-xs">
                    <span class="metric-label">{{ $t('pipelineSteps.' + step.step_name) }}</span>
                    <span class="text-weight-bold">{{ step.avg_duration.toFixed(2) }}s</span>
                  </div>
                  <q-linear-progress
                    :value="step.avg_duration / maxStepDuration"
                    :color="getStepColor(step.avg_duration)"
                    size="6px"
                    rounded
                    class="performance-progress"
                  />
                  <!-- Token info if available -->
                  <div v-if="step.avg_tokens" class="row items-center justify-between q-mt-xs">
                    <span class="text-caption text-grey-6">Tokens:</span>
                    <span class="text-caption">
                      ↑{{ Math.round(step.avg_tokens.input) }} ↓{{
                        Math.round(step.avg_tokens.output)
                      }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="text-center q-pa-md">{{ $t('noData') }}</div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Trending Topics -->
        <div class="col-12 col-md-6">
          <q-card flat class="pipeline-card pipeline-card--teal">
            <div class="glow-overlay glow-overlay--teal"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="local_fire_department" size="28px" color="teal-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">{{ $t('trendingQuestions') }}</div>
              </div>
              <q-list dense padding class="trending-list">
                <q-item
                  v-for="(topic, idx) in store.stats?.trending_topics"
                  :key="idx"
                  class="trending-item"
                >
                  <q-item-section avatar>
                    <q-avatar color="teal-7" text-color="white" size="32px">
                      {{ idx + 1 }}
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="">{{ topic.canonical_text }}</q-item-label>
                    <q-item-label caption class="">
                      {{ topic.frequency }}x asked
                      <span v-if="topic.variation_count > 1">
                        ({{ topic.variation_count }} variations)
                      </span>
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="!store.stats?.trending_topics.length" class="text-center q-pa-md">
                {{ $t('noTrendsYet') }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Charts Row 2 -->
      <div v-if="store.stats" class="row q-col-gutter-lg q-mb-md">
        <!-- Assistant Costs -->
        <div class="col-12 col-md-4">
          <q-card flat class="pipeline-card pipeline-card--amber">
            <div class="glow-overlay glow-overlay--amber"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="account_balance_wallet" size="28px" color="amber-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">{{ $t('costByAssistant') }}</div>
              </div>
              <q-list dense padding class="cost-list">
                <q-item
                  v-for="cost in store.stats?.assistant_costs"
                  :key="cost.assistant_id"
                  class="cost-item"
                >
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{
                      cost.assistant_name
                    }}</q-item-label>
                    <q-item-label caption class="">
                      {{ cost.total_tokens.toLocaleString() }} tokens
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label class="text-amber-4 text-weight-bold text-h6">
                      ${{ cost.estimated_cost_usd.toFixed(4) }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="!store.stats?.assistant_costs.length" class="text-center q-pa-md">
                {{ $t('noCostData') }}
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Top Users -->
        <div class="col-12 col-md-4">
          <q-card flat class="pipeline-card pipeline-card--cyan">
            <div class="glow-overlay glow-overlay--cyan"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="group" size="28px" color="cyan-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Top Users (30d)</div>
              </div>
              <q-list dense padding class="cost-list">
                <q-item
                  v-for="user in store.stats?.user_stats"
                  :key="user.user_id"
                  class="cost-item"
                >
                  <q-item-section avatar>
                    <q-avatar size="32px" color="cyan-8" text-color="white">
                      {{
                        user.full_name
                          ? user.full_name.charAt(0).toUpperCase()
                          : user.email.charAt(0).toUpperCase()
                      }}
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">
                      {{ user.full_name || user.email }}
                      <q-tooltip v-if="user.full_name">{{ user.email }}</q-tooltip>
                    </q-item-label>
                    <q-item-label caption class="">
                      {{ user.interaction_count }} interactions
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-item-label class="text-cyan-4 text-weight-bold">
                      {{ formatLargeNumber(user.total_tokens) }}
                    </q-item-label>
                    <q-item-label caption class="text-grey-6" style="font-size: 0.7em">
                      tokens
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="!store.stats?.user_stats.length" class="text-center q-pa-md">
                No user data
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Document Freshness -->
        <div class="col-12 col-md-4">
          <q-card flat class="pipeline-card pipeline-card--blue">
            <div class="glow-overlay glow-overlay--blue"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="description" size="28px" color="blue-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">
                  {{ $t('knowledgeBaseFreshness') }}
                </div>
              </div>
              <div
                v-for="fresh in store.stats?.document_freshness"
                :key="fresh.freshness_category"
                class="q-mb-md"
              >
                <div class="row items-center justify-between q-mb-xs">
                  <div class="col">
                    <q-badge
                      :color="getFreshnessColor(fresh.freshness_category)"
                      class="freshness-badge"
                    >
                      {{ fresh.freshness_category }}
                    </q-badge>
                  </div>
                  <div class="col-auto">
                    {{ fresh.doc_count }} docs ({{ fresh.percentage.toFixed(1) }}%)
                  </div>
                </div>
                <q-linear-progress
                  :value="fresh.percentage / 100"
                  :color="getFreshnessColor(fresh.freshness_category)"
                  size="6px"
                  rounded
                  class="performance-progress"
                />
              </div>
              <div v-if="!store.stats?.document_freshness.length" class="text-center q-pa-md">
                No documents
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Charts Row 3 (New) -->
      <div v-if="store.stats" class="row q-col-gutter-lg q-mt-md">
        <!-- Document Utilization -->
        <div class="col-12 col-md-8">
          <q-card flat class="pipeline-card pipeline-card--green">
            <div class="glow-overlay glow-overlay--green"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="insights" size="28px" color="green-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Top Utilized Documents</div>
              </div>
              <q-list dense padding class="cost-list">
                <q-item
                  v-for="doc in store.stats?.document_utilization"
                  :key="doc.file_name"
                  class="cost-item"
                >
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{ doc.file_name }}</q-item-label>
                    <q-item-label caption>{{ doc.connector_name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center">
                      <q-badge :color="getDocStatusColor(doc.status)" class="q-mr-sm">
                        {{ doc.status.toUpperCase() }}
                      </q-badge>
                      <q-item-label class="text-weight-bold"
                        >{{ doc.retrieval_count }}x</q-item-label
                      >
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="!store.stats?.document_utilization.length" class="text-center q-pa-md">
                No utilization data
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Connector Sync Rates -->
        <div class="col-12 col-md-4">
          <q-card flat class="pipeline-card pipeline-card--orange">
            <div class="glow-overlay glow-overlay--orange"></div>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="sync" size="28px" color="orange-5" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Connector Sync Reliability</div>
              </div>
              <q-list dense padding class="cost-list">
                <q-item
                  v-for="sync in store.stats?.connector_sync_rates"
                  :key="sync.connector_id"
                  class="cost-item"
                >
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{
                      sync.connector_name
                    }}</q-item-label>
                    <q-item-label caption>
                      {{ sync.successful_syncs }}/{{ sync.total_syncs }} success
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="text-right">
                      <div
                        :class="getSyncRateColorClass(sync.success_rate)"
                        class="text-weight-bold"
                      >
                        {{ sync.success_rate.toFixed(1) }}%
                      </div>
                      <div v-if="sync.avg_sync_duration" class="text-caption text-grey-6">
                        {{ sync.avg_sync_duration.toFixed(1) }}s avg
                      </div>
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-if="!store.stats?.connector_sync_rates.length" class="text-center q-pa-md">
                No sync data
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useAdvancedAnalyticsStore } from 'src/stores/advancedAnalyticsStore';

const store = useAdvancedAnalyticsStore();

const totalCost = computed(() => {
  return store.stats?.assistant_costs.reduce((sum, c) => sum + c.estimated_cost_usd, 0) || 0;
});

const totalTokens = computed(() => {
  return store.stats?.assistant_costs.reduce((sum, c) => sum + c.total_tokens, 0) || 0;
});

const maxStepDuration = computed(() => {
  return Math.max(...(store.stats?.step_breakdown.map((s) => s.avg_duration) || [1]));
});

function getTTFTProgress() {
  const p95 = store.stats?.ttft_percentiles?.p95 || 0;
  return Math.min(p95 / 5, 1); // Scale to 5s max
}

function getTTFTColor() {
  const p95 = store.stats?.ttft_percentiles?.p95 || 0;
  if (p95 < 2) return 'positive';
  if (p95 < 3.5) return 'warning';
  return 'negative';
}

function getStepColor(duration: number) {
  if (duration < 1) return 'positive';
  if (duration < 3) return 'warning';
  return 'negative';
}

function getFreshnessColor(category: string) {
  if (category.includes('Fresh')) return 'blue-4';
  if (category.includes('Aging')) return 'warning';
  return 'negative';
}

function getDocStatusColor(status: string) {
  if (status === 'hot') return 'negative';
  if (status === 'warm') return 'warning';
  return 'positive';
}

function getSyncRateColorClass(rate: number) {
  if (rate > 95) return 'text-positive';
  if (rate > 80) return 'text-warning';
  return 'text-negative';
}

function formatLargeNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
}

onMounted(async () => {
  // Always fetch on mount to ensure fresh data, then WebSocket updates will take over
  await store.fetchAnalytics();
});
</script>

<style lang="scss" scoped>
.analytics-container {
  // Hero Header
  .hero-header {
    .subtitle {
      font-weight: 300;
      letter-spacing: 1px;
      font-size: 0.9rem;
    }
  }

  // Status Badge
  .status-badge {
    background: rgba(255, 255, 255, 0.05);
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .live-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: #666;
      transition: all 0.3s ease;

      &--active {
        background-color: #00e676;
        box-shadow: 0 0 8px rgba(0, 230, 118, 1);
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
    background: linear-gradient(
      145deg,
      var(--q-secondary) 0%,
      rgba(var(--q-secondary-rgb), 0.8) 100%
    );
    border: 1px solid var(--q-sixth);
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
      &--amber {
        background: radial-gradient(circle at 50% 0%, #ffc10720 0%, transparent 70%);
      }
      &--red {
        background: radial-gradient(circle at 50% 0%, #ef535020 0%, transparent 70%);
      }
      &--cyan {
        background: radial-gradient(circle at 50% 0%, #00bcd420 0%, transparent 70%);
      }
      &--green {
        background: radial-gradient(circle at 50% 0%, #4caf5020 0%, transparent 70%);
      }
      &--orange {
        background: radial-gradient(circle at 50% 0%, #ff980020 0%, transparent 70%);
      }
    }
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
    }
  }

  // Progress bars
  .performance-progress {
    background: rgba(255, 255, 255, 0.05);
    height: 10px !important;
  }

  // List styling - More compact
  .trending-list {
    .trending-item {
      border-radius: 6px;
      margin-bottom: 0.25rem;
      transition: background 0.2s ease;
      padding: 0.25rem 0.5rem;

      &:hover {
        background: rgba(255, 255, 255, 0.05);
      }

      .q-avatar {
        font-size: 0.75rem;
      }

      .q-item__label {
        font-size: 0.85rem;
      }

      .q-item__label--caption {
        font-size: 0.7rem;
      }
    }
  }

  .cost-list {
    .cost-item {
      border-radius: 6px;
      margin-bottom: 0.25rem;
      transition: background 0.2s ease;
      padding: 0.25rem 0.5rem;

      &:hover {
        background: rgba(255, 255, 255, 0.05);
      }

      .q-item__label {
        font-size: 0.85rem;
      }

      .text-h6 {
        font-size: 1rem;
      }
    }
  }

  // Badges
  .freshness-badge {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.3rem 0.6rem;
    letter-spacing: 0.5px;
  }
}
</style>
