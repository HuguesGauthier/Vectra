<template>
  <q-expansion-item
    class="data-table-block q-my-sm"
    header-class="header-bg"
    expand-icon="arrow_drop_down"
    expand-icon-class="custom-chevron"
    :style="{ color: textColor }"
  >
    <template v-slot:header>
      <div class="row items-center full-width">
        <q-icon name="analytics" size="xs" class="q-mr-sm" :style="{ color: textColor }" />
        <div class="text-subtitle2 text-weight-bold flex-1" :style="{ color: textColor }">
          {{ $t('dataPreview') || 'Data Preview' }}
        </div>
        <div class="row q-gutter-x-sm q-ml-sm text-caption">
          <div class="badge-pill bg-opacity" :style="{ color: textColor }">
            {{ rows.length }} {{ $t('rows') }}
          </div>
          <div class="badge-pill bg-opacity" :style="{ color: textColor }">
            {{ columns?.length || 0 }} {{ $t('columns') }}
          </div>
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
            table-header-class="table-header text-weight-bold"
            :style="{ color: textColor }"
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
  textColor: string;
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
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.05);
  width: 100%;
  max-width: 100%;
}

.header-bg {
  background: transparent;
  border-bottom: 1px solid v-bind('`${textColor}26`');
}

.transparent-bg {
  background: transparent !important;
}

.table-container {
  max-height: 400px;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
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

::v-deep(.q-table) {
  width: 100%;
}

::v-deep(.table-header) {
  background-color: rgba(255, 255, 255, 0.1);
  border-bottom: 1px solid v-bind('`${textColor}4D`');
}

::v-deep(.q-expansion-item__toggle-icon) {
  color: v-bind('textColor') !important;
}

::v-deep(.q-table__card) {
  color: v-bind('textColor') !important;
}

::v-deep(.q-table th) {
  color: v-bind('textColor') !important;
  opacity: 0.9;
}

::v-deep(.q-table td) {
  color: v-bind('textColor') !important;
  opacity: 0.8;
  max-width: 300px;
  white-space: normal;
  word-break: break-word;
}
</style>
