<template>
  <div class="tech-sheet-block q-my-sm border-rounded-12 shadow-1">
    <div class="header q-pa-sm text-subtitle1 text-weight-bold row items-center">
      <q-icon name="list_alt" size="sm" class="q-mr-sm text-primary" />
      {{ data.title || $t('technicalDetails') || 'Technical Details' }}
    </div>

    <div class="content q-pa-sm">
      <template v-for="(section, sIndex) in data.sections" :key="`section-${sIndex}`">
        <div
          v-if="section.title"
          class="text-subtitle2 q-mt-sm q-mb-xs text-weight-bold text-grey-4"
        >
          {{ section.title }}
        </div>

        <table class="tech-table full-width">
          <tbody>
            <tr v-for="(item, iIndex) in section.items" :key="`item-${iIndex}`" class="tech-row">
              <td class="tech-label text-weight-medium q-pa-xs">{{ item.label }}</td>
              <td class="tech-value q-pa-xs">{{ item.value }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface TechSheetSection {
  title: string;
  items?: { label: string; value: string }[];
}

export interface TechSheet {
  title?: string;
  sections?: TechSheetSection[];
}

defineProps<{
  data: TechSheet;
}>();
</script>

<style scoped>
.tech-sheet-block {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.header {
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.tech-table {
  border-collapse: collapse;
}

.tech-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.2s ease;
}

.tech-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.tech-row:last-child {
  border-bottom: none;
}

.tech-label {
  width: 35%;
  color: var(--q-text-sub);
  vertical-align: top;
}

.tech-value {
  color: var(--q-text-main);
}
</style>
