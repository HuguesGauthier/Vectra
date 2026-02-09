<template>
  <q-form ref="formRef" @submit.prevent="submit" class="q-gutter-md">
    <div class="row q-col-gutter-sm">
      <div class="col-12 text-subtitle2 q-mb-sm text-grey-4">Azure Authentication</div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.tenant_id"
          label="Tenant ID"
          dark
          outlined
          dense
          :rules="[(val) => !!val || $t('fieldRequired')]"
        />
      </div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.client_id"
          label="Client ID"
          dark
          outlined
          dense
          :rules="[(val) => !!val || $t('fieldRequired')]"
        />
      </div>

      <div class="col-12">
        <q-input
          v-model="formData.client_secret"
          label="Client Secret"
          type="password"
          dark
          outlined
          dense
          :rules="[(val) => !!val || $t('fieldRequired')]"
        />
      </div>
    </div>

    <q-separator dark class="q-my-md" />

    <div class="row q-col-gutter-sm">
      <div class="col-12 text-subtitle2 q-mb-sm text-grey-4">Target</div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.sharepoint_site_name"
          label="Site Name (Optional)"
          hint="e.g. 'marketing'. Leave empty for Root site."
          dark
          outlined
          dense
        />
      </div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.folder_path"
          label="Folder Path (Optional)"
          hint="e.g. 'Shared Documents/Reports'"
          dark
          outlined
          dense
        />
      </div>

      <div class="col-12">
        <q-toggle v-model="formData.recursive" label="Scan Recursively" dark color="accent" />
      </div>
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { Connector } from 'src/models/Connector';
import type { QForm } from 'quasar';

// --- PROPS ---
// Use defineModel to handle prop mutation safely (standard pattern)
const data = defineModel<Connector>('data', { required: true });

// --- STATE ---
const formRef = ref<QForm | null>(null);
const formData = ref({
  tenant_id: '',
  client_id: '',
  client_secret: '',
  sharepoint_site_name: '',
  folder_path: '',
  recursive: true,
});

// --- INIT ---
onMounted(() => {
  if (data.value.configuration) {
    const c = data.value.configuration;
    formData.value = {
      tenant_id: c.tenant_id || '',
      client_id: c.client_id || '',
      client_secret: c.client_secret || '',
      sharepoint_site_name: c.sharepoint_site_name || '',
      folder_path: c.folder_path || '',
      recursive: c.recursive !== false, // Default true
    };
  }
});

// --- EXPOSED METHODS ---
async function submit(): Promise<boolean> {
  if (!formRef.value) return false;

  const valid = await formRef.value.validate();
  if (!valid) return false;

  // Sync back to main connector object via model
  if (!data.value.configuration) data.value.configuration = {};

  // Use Object.assign on the reactive model value
  Object.assign(data.value.configuration, {
    tenant_id: formData.value.tenant_id,
    client_id: formData.value.client_id,
    client_secret: formData.value.client_secret,
    sharepoint_site_name: formData.value.sharepoint_site_name || null,
    folder_path: formData.value.folder_path || null,
    recursive: formData.value.recursive,
  });

  return true;
}

defineExpose({ submit });
</script>
