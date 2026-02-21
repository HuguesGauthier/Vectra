<template>
  <q-expansion-item
    class="data-table-block q-my-sm"
    header-class="header-bg"
    expand-icon-class="text-grey-4"
    expand-icon="arrow_drop_down"
  >
    <template v-slot:header>
      <div class="row items-center full-width">
        <q-icon name="analytics" size="xs" class="q-mr-sm text-grey-4" />
        <div class="text-subtitle2 text-weight-bold flex-1">
          {{ $t('dataPreview') || 'Data Preview' }}
        </div>
        <div class="row q-gutter-x-sm q-ml-sm text-caption">
          <div class="badge-pill bg-opacity">{{ rows.length }} {{ $t('rows') }}</div>
          <div class="badge-pill bg-opacity">{{ columns?.length || 0 }} {{ $t('columns') }}</div>
        </div>
      </div>
    </template>

    <q-card class="transparent-bg shadow-none">
      <q-card-section class="q-pa-none">
        <div class="table-container">
          <q-table
            flat
            dense
            dark
            :rows="rows"
            :columns="columns"
            row-key="id"
            :rows-per-page-options="[10, 25, 50, 0]"
            class="transparent-bg no-border-radius"
            table-header-class="table-header text-weight-bold text-grey-4"
          />
        </div>
      </q-card-section>
    </q-card>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  data: any; // eslint-disable-line @typescript-eslint/no-explicit-any
}>();

const rows = computed(() => {
  if (Array.isArray(props.data)) {
    return props.data;
  } else if (props.data?.data) {
    return props.data.data;
  }
  return [];
});

const columns = computed(() => {
  if (Array.isArray(props.data) && props.data.length > 0) {
    // Auto-detect from first row
    return Object.keys(props.data[0]).map((key) => ({
      name: key,
      field: key,
      label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
      sortable: true,
      align: 'left',
    }));
  } else if (props.data?.columns) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return props.data.columns.map((c: any) => ({
      name: c.name || c,
      field: c.name || c,
      label: c.label || c.name || c,
      sortable: true,
      align: 'left',
    }));
  }
  return [];
});
</script>

<style scoped>
.data-table-block {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.header-bg {
  background: rgba(0, 0, 0, 0.2);
}

.transparent-bg {
  background: transparent !important;
}

.table-container {
  max-height: 400px;
  overflow-y: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.badge-pill {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  display: flex;
  align-items: center;
}

.bg-opacity {
  background: rgba(255, 255, 255, 0.1) !important;
}

/* Custom scrollbar for table container */
.table-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.table-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}
.table-container::-webkit-scrollbar-track {
  background: transparent;
}

::v-deep(.table-header) {
  background-color: rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid var(--q-primary);
}
</style>
