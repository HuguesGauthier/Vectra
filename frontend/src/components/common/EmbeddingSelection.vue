<template>
  <div class="row q-col-gutter-lg justify-center">
    <div v-for="provider in providers" :key="provider.id" class="col-12 col-md-4">
      <q-card
        flat
        class="selection-card full-height column justify-between"
        :class="{
          selected: selectable && modelValue === provider.id,
          disabled: selectable && provider.disabled,
          selectable: selectable,
        }"
        v-ripple="selectable && !provider.disabled"
        @click="selectable && !provider.disabled ? handleSelect(provider.id) : null"
        style="min-height: 280px"
      >
        <div v-if="selectable && modelValue === provider.id" class="selected-overlay">
          <q-icon name="check_circle" color="accent" size="32px" />
        </div>

        <AppTooltip v-if="provider.disabled">
          {{ notConfiguredMessage }}
        </AppTooltip>

        <q-card-section class="col-grow column items-center text-center q-pt-lg">
          <div class="q-mb-md relative-position">
            <img :src="provider.logo" style="width: 64px; height: 64px" />
            <q-badge
              v-if="provider.badge"
              floating
              :color="provider.badgeColor"
              rounded
              class="q-px-sm q-py-xs"
              style="top: -5px; right: -15px"
            >
              {{ provider.badge }}
            </q-badge>
          </div>

          <div class="text-h6 text-weight-bold q-mb-xs">{{ provider.name }}</div>
          <div class="text-caption q-mb-md">{{ provider.tagline }}</div>

          <div class="text-body2 full-width">
            {{ provider.description }}
          </div>
        </q-card-section>

        <div class="row justify-center q-pb-md" v-if="showConfigButton">
          <q-btn
            flat
            no-caps
            dense
            color="accent"
            icon="settings"
            :label="configLabel"
            size="sm"
            :disable="provider.disabled && disableConfigWhenDisabled"
            @click.stop="$emit('configure', provider.id)"
          >
            <q-tooltip class="text-body2" v-if="configTooltip">{{ configTooltip }}</q-tooltip>
          </q-btn>
        </div>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';
import AppTooltip from 'src/components/common/AppTooltip.vue';

export interface ProviderOption {
  id: string;
  name: string;
  tagline?: string;
  description?: string;
  logo: string;
  badge?: string;
  badgeColor?: string;
  disabled?: boolean;
}

const props = defineProps({
  modelValue: {
    type: String as PropType<string | undefined>,
    default: '',
  },
  providers: {
    type: Array as PropType<ProviderOption[]>,
    default: () => [],
  },
  notConfiguredMessage: {
    type: String,
    default: 'Not Configured',
  },
  showConfigButton: {
    type: Boolean,
    default: false,
  },
  configLabel: {
    type: String,
    default: 'Settings',
  },
  configTooltip: {
    type: String,
    default: '',
  },
  disableConfigWhenDisabled: {
    type: Boolean,
    default: false,
  },
  selectable: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['update:modelValue', 'configure']);

function handleSelect(id: string) {
  if (props.selectable) {
    emit('update:modelValue', id);
  }
}
</script>

<style scoped>
.selection-card {
  background: var(--q-secondary);
  border: 1px solid var(--q-third);
  transition: all 0.3s ease;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.selection-card.selectable {
  cursor: pointer;
}

.selection-card.selectable:hover {
  border-color: var(--q-accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.selection-card.disabled:not(.selected) {
  opacity: 0.5;
  filter: grayscale(100%);
  cursor: not-allowed !important;
  transform: none !important;
  box-shadow: none !important;
  border-color: var(--q-third) !important;
}

.selection-card.selected {
  border-color: var(--q-accent);
  background: #252525;
  box-shadow: 0 0 0 2px var(--q-accent);
}

.selected-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}
</style>
