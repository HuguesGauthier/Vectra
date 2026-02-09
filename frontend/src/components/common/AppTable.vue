<template>
  <q-table
    :rows="rows"
    :columns="columns"
    :row-key="rowKey"
    :loading="loading"
    :filter="filter"
    flat
    separator="horizontal"
    :pagination="pagination"
    :hide-pagination="hidePagination"
    :style="tableStyle"
    v-bind="$attrs"
  >
    <!-- Top left slot for search and actions -->
    <template v-slot:top-left>
      <slot name="top-left">
        <div class="row items-center q-gutter-x-sm">
          <!-- Add button slot -->
          <slot name="add-button"></slot>

          <!-- Search input -->
          <q-input
            v-if="showSearch"
            v-model="internalFilter"
            dense
            outlined
            bg-color="primary"
            class="custom-search q-mr-sm"
            :style="{ minWidth: searchMinWidth }"
            :placeholder="$t('search')"
          >
            <template v-slot:append>
              <q-icon name="search" />
            </template>
          </q-input>

          <!-- Additional top-left content -->
          <slot name="top-left-extra"></slot>
        </div>
      </slot>
    </template>

    <!-- Top right slot -->
    <template v-slot:top-right>
      <slot name="top-right"></slot>
    </template>

    <!-- No data slot -->
    <template v-slot:no-data>
      <slot name="no-data">
        <div class="full-width column flex-center q-pa-xl">
          <q-icon :name="noDataIcon" size="64px" color="main" class="q-mb-md" />
          <div class="text-h6 q-mb-xs">{{ noDataTitle }}</div>
          <div class="text-subtitle2 q-mb-lg">
            {{ noDataMessage }}
          </div>
          <slot name="no-data-action"></slot>
        </div>
      </slot>
    </template>

    <!-- Body slot for custom row rendering -->
    <template v-slot:body="props">
      <slot name="body" :props="props">
        <q-tr :props="props">
          <q-td v-for="col in props.cols" :key="col.name" :props="props">
            {{ col.value }}
          </q-td>
        </q-tr>
      </slot>
    </template>
  </q-table>
</template>

<script setup lang="ts" generic="T">
import { ref, watch } from 'vue';
import { type QTableColumn } from 'quasar';

// --- TYPES ---
interface Props {
  rows: T[];
  columns: QTableColumn[];
  rowKey?: string;
  loading?: boolean;
  filter?: string;
  showSearch?: boolean;
  searchMinWidth?: string;
  pagination?: object;
  hidePagination?: boolean;
  noDataIcon?: string;
  noDataTitle?: string;
  noDataMessage?: string;
  tableStyle?: string;
}

// --- PROPS ---
const props = withDefaults(defineProps<Props>(), {
  rowKey: 'id',
  loading: false,
  filter: '',
  showSearch: true,
  searchMinWidth: '300px',
  pagination: () => ({ rowsPerPage: 0 }),
  hidePagination: true,
  noDataIcon: 'inbox',
  noDataTitle: 'No data found',
  noDataMessage: 'Add your first item to get started.',
  tableStyle: 'background-color: var(--q-fifth)',
});

// --- EMITS ---
const emit = defineEmits<{
  'update:filter': [value: string];
}>();

// --- SLOTS ---
defineSlots<{
  'top-left'?: (props: unknown) => unknown;
  'add-button'?: (props: unknown) => unknown;
  'top-left-extra'?: (props: unknown) => unknown;
  'top-right'?: (props: unknown) => unknown;
  'no-data'?: (props: unknown) => unknown;
  'no-data-action'?: (props: unknown) => unknown;
  body?: (props: {
    props: { row: T; rowIndex: number; cols: QTableColumn[]; [key: string]: unknown };
  }) => unknown;
}>();

// --- STATE ---
const internalFilter = ref(props.filter);

// --- WATCHERS ---
watch(
  () => props.filter,
  (newVal) => {
    internalFilter.value = newVal;
  },
);

watch(internalFilter, (newVal) => {
  emit('update:filter', newVal);
});
</script>

<style scoped>
.custom-search :deep(.q-field__control):before,
.custom-search :deep(.q-field__control):after {
  border-color: var(--q-third) !important;
  border-width: 1px !important;
}

.custom-search :deep(.q-field__control) {
  border-radius: 8px;
}

.q-table__card {
  background-color: var(--q-fifth) !important;
  border-radius: 8px;
}

/* Override table row borders to use theme color */
:deep(.q-table thead tr),
:deep(.q-table tbody tr) {
  border-color: var(--q-third);
}

:deep(.q-table th),
:deep(.q-table td) {
  border-color: var(--q-sixth);
}
</style>
