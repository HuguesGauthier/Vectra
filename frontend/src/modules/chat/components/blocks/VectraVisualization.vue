<template>
  <div class="visualization-block q-my-md shadow-2 relative-position border-rounded-12">
    <!-- Header -->
    <div class="header-bg row items-center q-pa-sm border-bottom">
      <q-icon name="insert_chart" size="sm" class="q-mr-sm text-primary" />
      <div class="text-subtitle2 text-weight-bold flex-1">
        {{ $t('visualization') || 'Visualization' }}
      </div>
    </div>

    <!-- Chart Container -->
    <div class="chart-container q-pa-md transparent-bg">
      <apexchart
        v-if="chartOptions"
        :type="chartType"
        :options="chartOptions"
        :series="chartSeries"
        height="300"
        width="100%"
      />
      <!-- Fallback empty state -->
      <div v-else class="row flex-center full-height text-grey italic q-pa-xl">
        Invalid chart configuration
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuasar } from 'quasar';

const props = defineProps<{
  config: any; // eslint-disable-line @typescript-eslint/no-explicit-any
}>();

const $q = useQuasar();

// Extract type safely
const chartType = computed(() => {
  return props.config?.chart?.type || props.config?.viz_type || 'bar';
});

// Build series (handling Cartesian vs Circular)
const chartSeries = computed(() => {
  const series = props.config?.series;
  if (!series || !Array.isArray(series)) return [];

  if (series.length > 0) {
    const first = series[0];
    if (typeof first === 'number' || typeof first === 'string') {
      // Circular (Pie, Donut)
      return series;
    } else {
      // Cartesian (Bar, Line, etc)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return series.map((s: any) => ({
         
        ...s,
        data: s.data || [],
      }));
    }
  }
  return [];
});

// Build the full options object respecting Quasar's dark mode
const chartOptions = computed(() => {
  if (!props.config) return null;

  const themeMode = $q.dark.isActive ? 'dark' : 'light';
  const rawChart = props.config.chart || {};

  return {
    ...props.config, // Spread base
    labels: props.config.labels || props.config.xaxis?.categories || [],
    chart: {
      ...rawChart,
      type: chartType.value,
      background: 'transparent',
      toolbar: { show: false },
      fontFamily: 'inherit',
    },
    theme: {
      mode: themeMode,
      ...(props.config.theme || {}),
    },
    dataLabels: {
      enabled: true,
      ...(props.config.dataLabels || {}),
    },
    legend: {
      show: true,
      position: 'bottom',
      horizontalAlign: 'center',
      ...(props.config.legend || {}),
    },
  };
});
</script>

<style scoped>
.visualization-block {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.header-bg {
  background: rgba(0, 0, 0, 0.2);
}

.border-bottom {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.transparent-bg {
  background: transparent !important;
}

.chart-container {
  min-height: 300px;
}
</style>
