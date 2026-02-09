<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs q-mt-lg">
      {{ $t('sharePointConfiguration') }}
    </div>

    <q-input
      :model-value="modelValue.siteUrl"
      @update:model-value="updateField('siteUrl', $event)"
      :label="$t('labelSiteUrl')"
      hint="https://yourtenant.sharepoint.com/sites/yoursite"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.tenantId"
      @update:model-value="updateField('tenantId', $event)"
      :label="$t('labelTenantId')"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.clientSecret"
      @update:model-value="updateField('clientSecret', $event)"
      :label="$t('labelClientSecret')"
      type="password"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />
  </div>
</template>

<script setup lang="ts">
// --- DEFINITIONS ---
interface SharePointConfig {
  siteUrl: string;
  tenantId: string;
  clientSecret: string;
}

const modelValue = defineModel<SharePointConfig>({ required: true });

// --- FUNCTIONS ---
function updateField(field: keyof SharePointConfig, value: string | number | null) {
  modelValue.value = { ...modelValue.value, [field]: String(value || '') };
}
</script>
