<template>
  <q-expansion-item
    class="visualization-block q-my-sm"
    header-class="header-bg"
    expand-icon="arrow_drop_down"
    expand-icon-class="custom-chevron"
    :style="{ color: textColor }"
    default-opened
  >
    <template v-slot:header>
      <div class="row items-center full-width">
        <q-icon name="insert_chart" size="xs" class="q-mr-sm" :style="{ color: textColor }" />
        <div class="text-subtitle2 text-weight-bold flex-1" :style="{ color: textColor }">
          {{ $t('visualization') || 'Visualization' }}
        </div>
        <div class="row q-gutter-x-sm q-ml-sm text-caption">
          <div class="badge-pill bg-opacity" :style="{ color: textColor }">
            {{ chartTypeLabel }}
          </div>
        </div>
      </div>
    </template>

    <q-card class="transparent-bg shadow-none">
      <q-card-section class="q-pa-md">
        <div class="chart-container">
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
      </q-card-section>
    </q-card>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuasar } from 'quasar';
import apexchart from 'vue3-apexcharts';
import type { ApexOptions } from 'apexcharts';

const props = defineProps<{
  config: any; // eslint-disable-line @typescript-eslint/no-explicit-any
  textColor: string;
}>();

const $q = useQuasar();

// Extract type safely
const chartType = computed(() => {
  return props.config?.chart?.type || props.config?.viz_type || 'bar';
});

const chartTypeLabel = computed(() => {
  const type = chartType.value;
  return type.charAt(0).toUpperCase() + type.slice(1);
});

// Build series (handling Cartesian vs Circular)
const chartSeries = computed(() => {
  const series = props.config?.series;
  if (!series || !Array.isArray(series)) return [];

  if (series.length > 0) {
    const first = series[0];
    if (typeof first === 'number' || typeof first === 'string') {
      // Circular (Pie, Donut)
      return series.map((s) => Number(s));
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
const chartOptions = computed<ApexOptions | null>(() => {
  if (!props.config) return null;

  const themeMode = $q.dark.isActive ? 'dark' : 'light';
  const isCircular = ['pie', 'donut', 'radialBar', 'polarArea'].includes(chartType.value);

  // Extract explicit values from config to prevent pollution
  const configLabels = props.config.labels || props.config.xaxis?.categories || [];

  const commonStyle = {
    fontSize: '11px',
    fontFamily: 'inherit',
    fontWeight: 400,
    colors: props.textColor,
  };

  const options: ApexOptions = {
    labels: configLabels,
    chart: {
      type: chartType.value,
      background: 'transparent',
      toolbar: {
        show: true,
        tools: {
          download: true,
          selection: true,
          zoom: true,
          zoomin: true,
          zoomout: true,
          pan: true,
          reset: true,
        },
      },
      fontFamily: 'inherit',
      animations: { enabled: true },
      ...(props.config.chart || {}),
    },
    theme: {
      mode: themeMode,
      palette: 'palette1',
      ...(props.config.theme || {}),
    },
    dataLabels: {
      enabled: true,
      style: {
        fontSize: '12px',
        fontFamily: 'inherit',
        fontWeight: 'bold',
        colors: [props.textColor],
      },
      ...(props.config.dataLabels || {}),
    },
    legend: {
      show: true,
      position: 'bottom',
      horizontalAlign: 'center',
      labels: {
        colors: props.textColor,
        useSeriesColors: false,
      },
      ...(props.config.legend || {}),
    },
    tooltip: {
      theme: themeMode,
      style: {
        fontSize: '12px',
        fontFamily: 'inherit',
      },
      ...(props.config.tooltip || {}),
    },
  };

  if (!isCircular) {
    options.xaxis = {
      type: 'category',
      labels: {
        style: commonStyle,
        ...(props.config.xaxis?.labels || {}),
      },
      ...(props.config.xaxis || {}),
    };
    options.yaxis = {
      labels: {
        style: commonStyle,
        ...(props.config.yaxis?.labels || {}),
      },
      ...(props.config.yaxis || {}),
    };
  } else {
    // Pie charts specific
    options.stroke = { show: false };
    options.plotOptions = {
      pie: {
        expandOnClick: true,
        dataLabels: { offset: -5 },
      },
    };
  }

  return options;
});
</script>

<style scoped>
.visualization-block {
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

.badge-pill {
  background: rgba(255, 255, 255, 0.15);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  display: flex;
  align-items: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.bg-opacity {
  background: rgba(255, 255, 255, 0.1) !important;
}

.chart-container {
  min-height: 300px;
}

::v-deep(.q-expansion-item__toggle-icon) {
  color: v-bind('textColor') !important;
}

/* ApexCharts Toolbar Styling */
:deep(.apexcharts-toolbar svg) {
  fill: v-bind('textColor') !important;
}

:deep(.apexcharts-menu) {
  background: var(--q-secondary) !important;
  border: 1px solid var(--q-sixth) !important;
  color: v-bind('textColor') !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
}

:deep(.apexcharts-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1) !important;
}
</style>
