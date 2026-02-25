<template>
  <div class="q-my-md">
    <q-table
      flat
      bordered
      :rows="data.data"
      :columns="data.columns"
      row-key="id"
      dense
      :pagination="{ rowsPerPage: 5 }"
      hide-pagination
      class="bg-transparent"
      :class="[`text-${assistant?.avatar_text_color || 'white'}`]"
    >
      <template v-slot:top>
        <div class="row items-center full-width">
          <q-icon name="table_chart" size="sm" class="q-mr-sm" />
          <div class="text-subtitle2">Data Table</div>
          <q-space />
          <q-btn icon="download" flat round dense @click="downloadCSV(data.columns, data.data)">
            <q-tooltip>Download CSV</q-tooltip>
          </q-btn>
        </div>
      </template>
    </q-table>
  </div>
</template>

<script setup lang="ts">
import { usePublicChatStore } from 'src/stores/publicChatStore';
import type { Assistant } from 'src/services/assistantService';

const chatStore = usePublicChatStore();
void chatStore;

interface TableColumn {
  name: string;
  label: string;
  field: string;
  sortable?: boolean;
}

interface TableData {
  columns: TableColumn[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
}

defineProps<{
  data: TableData;
  assistant: Assistant | null;
}>();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function downloadCSV(columns: any[], data: any[]) {
  if (!columns || !data) return;

  const headers = columns.map((c) => c.label).join(',');
  const rows = data.map((row) =>
    columns
      .map((c) => {
        const val = row[c.field];
        // Handle commas/quotes in CSV
        return `"${String(val).replace(/"/g, '""')}"`;
      })
      .join(','),
  );

  const csvContent = [headers, ...rows].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', 'export_data.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
</script>
