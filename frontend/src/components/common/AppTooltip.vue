<template>
  <q-tooltip :delay="500" :offset="[0, 10]" class="bg-grey-9 text-body2" v-bind="$attrs">
    <slot />
  </q-tooltip>
</template>

<script setup lang="ts">
/**
 * AppTooltip - Standardized tooltip wrapper component
 *
 * Wraps Quasar's q-tooltip with consistent defaults:
 * - 500ms delay before showing
 * - 10px vertical offset
 * - Dark background with readable body text
 *
 * All q-tooltip props can be overridden via attributes.
 *
 * @example
 * <q-btn icon="add">
 *   <AppTooltip>{{ $t('create') }}</AppTooltip>
 * </q-btn>
 *
 * @example Custom anchor
 * <q-btn>
 *   <AppTooltip anchor="top middle">Different position</AppTooltip>
 * </q-btn>
 */
</script>
