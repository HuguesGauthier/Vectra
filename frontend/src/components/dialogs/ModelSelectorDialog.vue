<template>
  <q-dialog v-model="isOpen"  >
    <q-card class="model-selector-card" style="min-width: 1000px; max-height: 85vh;">

      <!-- Header -->
      <q-card-section class="model-selector-header">
        <div class="row items-center no-wrap">
          <div class="col">
            <div class="text-h5 text-weight-bold">{{ $t('selectModel') }}</div>
            <div class="text-caption text-grey-5">{{ providerName }}</div>
          </div>
          <q-btn icon="close" flat round dense @click="isOpen = false" color="grey-5" />
        </div>

        <!-- Search -->
        <q-input
          v-model="searchQuery"
          :placeholder="$t('searchModels')"
          outlined
          dense
          rounded
          class="q-mt-md search-input"
          clearable
          autofocus
        >
          <template v-slot:prepend>
            <q-icon name="search" color="grey-5" />
          </template>
        </q-input>
      </q-card-section>

      <!-- Model Grid -->
      <q-card-section class="model-grid-container q-pt-none col scroll">

        <template v-for="cat in visibleCategories" :key="cat.key">
          <div class="category-label">
            <q-icon :name="cat.icon" size="18px" :color="cat.color" class="q-mr-xs" />
            {{ cat.label }}
          </div>
          <div class="model-grid">
            <div
              v-for="model in modelsByCategory[cat.key]"
              :key="model.id"
              class="model-card"
              :class="{
                'model-card--selected': selectedModelId === model.id,
                [`model-card--${model.category}`]: true,
              }"
              @click="selectModel(model)"
            >
              <!-- Selection indicator -->
              <div v-if="selectedModelId === model.id" class="selected-check">
                <q-icon name="check_circle" color="positive" size="22px" />
              </div>

              <!-- Category badge -->
              <q-badge
                :color="getCategoryColor(model.category)"
                :label="getCategoryLabel(model.category)"
                class="category-badge"
                rounded
              />

              <div class="model-name">{{ model.name }}</div>
              <div class="model-desc">{{ getModelDescription(model) }}</div>

              <!-- Pricing -->
              <div class="model-pricing">
                <div class="price-row">
                  <span class="price-label">{{ $t('inputPrice') }}</span>
                  <span class="price-value">${{ model.input_price.toFixed(2) }}</span>
                </div>
                <div class="price-row">
                  <span class="price-label">{{ $t('outputPrice') }}</span>
                  <span class="price-value">${{ model.output_price.toFixed(2) }}</span>
                </div>
                <div class="price-unit">{{ $t('perMillionTokens') }}</div>
              </div>
            </div>
          </div>
        </template>

        <!-- Empty state -->
        <div v-if="filteredModels.length === 0" class="empty-state">
          <q-icon name="search_off" size="48px" color="grey-6" />
          <div class="text-grey-5 q-mt-sm">{{ $t('noModelsFound') }}</div>
        </div>
      </q-card-section>

      <!-- Footer -->
      <q-card-actions class="model-selector-footer" align="right">
        <q-btn flat :label="$t('cancel')" color="grey-5" @click="isOpen = false" />
        <q-btn
          unelevated
          :label="$t('confirmSelection')"
          color="accent"
          :disable="!selectedModelId"
          @click="confirmSelection"
          class="confirm-btn"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ModelInfo } from 'src/models/ProviderOption';

const i18n = useI18n();

const props = defineProps({
  providerName: {
    type: String,
    default: '',
  },
  models: {
    type: Array as PropType<ModelInfo[]>,
    default: () => [],
  },
  currentModelId: {
    type: String,
    default: '',
  },
  context: {
    type: String as PropType<'chat' | 'embedding' | 'transcription' | 'rerank' | 'extraction'>,
    default: 'chat',
  },
});

const emit = defineEmits(['update:isOpen', 'select']);
const isOpen = defineModel<boolean>('isOpen', { default: false });

const searchQuery = ref('');
const selectedModelId = ref('');

// Initialize selection when dialog opens
watch(isOpen, (val) => {
  if (val) {
    selectedModelId.value = props.currentModelId;
    searchQuery.value = '';
  }
});

function getModelDescription(model: ModelInfo) {
  // Try contextual key first (e.g. model_desc_transcription["id"])
  if (props.context && props.context !== 'chat') {
    const contextKey = `model_desc_${props.context}["${model.id}"]`;
    if (i18n.te(contextKey)) {
      return i18n.t(contextKey);
    }
  }

  // Fallback to common model_desc
  const key = `model_desc["${model.id}"]`;
  return i18n.te(key) ? i18n.t(key) : model.description;
}

const filteredModels = computed(() => {
  if (!searchQuery.value) return props.models;
  const q = searchQuery.value.toLowerCase();
  return props.models.filter((m) => {
    const localizedDesc = getModelDescription(m).toLowerCase();
    return (
      m.name.toLowerCase().includes(q) ||
      localizedDesc.includes(q) ||
      m.id.toLowerCase().includes(q)
    );
  });
});

const categoryOrder = ['flagship', 'reasoning', 'balanced', 'economy'] as const;

const categoryMeta: Record<string, { icon: string; color: string }> = {
  flagship: { icon: 'stars', color: 'amber' },
  reasoning: { icon: 'psychology', color: 'purple-4' },
  balanced: { icon: 'balance', color: 'light-blue-4' },
  economy: { icon: 'bolt', color: 'green-4' },
};

const modelsByCategory = computed(() => {
  const grouped: Record<string, ModelInfo[]> = {};
  for (const model of filteredModels.value) {
    if (!grouped[model.category]) grouped[model.category] = [];
    grouped[model.category]!.push(model);
  }
  return grouped;
});

const visibleCategories = computed(() => {
  return categoryOrder
    .filter((key) => modelsByCategory.value[key]?.length)
    .map((key) => ({
      key,
      label: getCategoryLabel(key),
      icon: categoryMeta[key]?.icon ?? 'help',
      color: categoryMeta[key]?.color ?? 'grey-5',
    }));
});

function getCategoryColor(category: string): string {
  const map: Record<string, string> = {
    flagship: 'amber-8',
    reasoning: 'purple-6',
    balanced: 'light-blue-7',
    economy: 'green-7',
  };
  return map[category] || 'grey-7';
}

function getCategoryLabel(category: string): string {
  const map: Record<string, string> = {
    flagship: i18n.t('categoryFlagship'),
    reasoning: i18n.t('categoryReasoning'),
    balanced: i18n.t('categoryBalanced'),
    economy: i18n.t('categoryEconomy'),
  };
  return map[category] || category;
}

function selectModel(model: ModelInfo) {
  selectedModelId.value = model.id;
}

function confirmSelection() {
  emit('select', selectedModelId.value);
  isOpen.value = false;
}
</script>

<style scoped>
.model-selector-card {
  background: var(--q-dark, #1a1a2e);
  display: flex;
  flex-direction: column;
}


.model-selector-header {
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 1;
}

.search-input :deep(.q-field__control) {
  background: rgba(255, 255, 255, 0.05);
}

.model-grid-container {
  flex: 1;
  padding-bottom: 20px;
}


.category-label {
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.5);
  margin: 20px 0 12px 0;
}

.category-label:first-child {
  margin-top: 8px;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.model-card {
  position: relative;
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.model-card:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
}

.model-card--selected {
  border-color: var(--q-positive) !important;
  background: rgba(76, 175, 80, 0.08) !important;
  box-shadow: 0 0 0 1px var(--q-positive);
}

.selected-check {
  position: absolute;
  top: 10px;
  right: 10px;
}

.category-badge {
  align-self: flex-start;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  margin-bottom: 10px;
}

.model-name {
  font-size: 1rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
  margin-bottom: 6px;
}

.model-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.4;
  flex: 1;
  margin-bottom: 12px;
}

.model-pricing {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 8px 10px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
}

.price-row + .price-row {
  margin-top: 2px;
}

.price-label {
  color: rgba(255, 255, 255, 0.4);
}

.price-value {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.price-unit {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.3);
  text-align: right;
  margin-top: 2px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
}

.model-selector-footer {
  position: sticky;
  bottom: 0;
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 12px 16px;
}

.confirm-btn {
  min-width: 140px;
}

/* Light mode overrides */
.body--light .model-selector-card {
  background: #f8f9fa;
}

.body--light .model-selector-header {
  background: rgba(0, 0, 0, 0.02);
  border-bottom-color: rgba(0, 0, 0, 0.08);
}

.body--light .search-input :deep(.q-field__control) {
  background: rgba(0, 0, 0, 0.04);
}

.body--light .category-label {
  color: rgba(0, 0, 0, 0.5);
}

.body--light .model-card {
  background: white;
  border-color: rgba(0, 0, 0, 0.08);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.body--light .model-card:hover {
  background: white;
  border-color: rgba(0, 0, 0, 0.15);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.body--light .model-card--selected {
  background: rgba(76, 175, 80, 0.05) !important;
}

.body--light .model-name {
  color: rgba(0, 0, 0, 0.87);
}

.body--light .model-desc {
  color: rgba(0, 0, 0, 0.55);
}

.body--light .model-pricing {
  background: rgba(0, 0, 0, 0.03);
}

.body--light .price-label {
  color: rgba(0, 0, 0, 0.45);
}

.body--light .price-value {
  color: rgba(0, 0, 0, 0.8);
}

.body--light .price-unit {
  color: rgba(0, 0, 0, 0.35);
}

.body--light .model-selector-footer {
  background: rgba(0, 0, 0, 0.02);
  border-top-color: rgba(0, 0, 0, 0.08);
}
</style>
