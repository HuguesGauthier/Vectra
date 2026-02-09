<template>
  <q-form ref="formRef" @submit.prevent="submit" class="q-gutter-md">
    <div class="row q-col-gutter-sm">
      <div class="col-12 text-subtitle2 q-mb-sm text-grey-4">Confluence Connection</div>

      <div class="col-12">
        <q-input
          v-model="formData.url"
          label="Confluence Base URL"
          hint="https://yourcompany.atlassian.net/wiki"
          dark
          outlined
          dense
          :rules="[
            (val) => !!val || $t('fieldRequired'),
            (val) => val.startsWith('http') || 'Must start with http:// or https://',
          ]"
        />
      </div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.username"
          label="Atlassian Account Email"
          dark
          outlined
          dense
          :rules="[
            (val) => !!val || $t('fieldRequired'),
            (val) => val.includes('@') || 'Must be a valid email',
          ]"
        />
      </div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.api_token"
          label="API Token"
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
      <div class="col-12 text-subtitle2 q-mb-sm text-grey-4">Scopes</div>

      <div class="col-12 col-md-6">
        <q-input
          v-model="formData.space_key"
          label="Space Key (Optional)"
          hint="e.g. 'DS' or 'ENG'. Leave empty for all spaces."
          dark
          outlined
          dense
        />
      </div>

      <div class="col-12">
        <q-toggle
          v-model="formData.include_attachments"
          label="Index Attachments (PDF, Images)"
          dark
          color="accent"
        />
      </div>
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { Connector } from 'src/models/Connector';
import type { QForm } from 'quasar';

// --- PROPS ---
const data = defineModel<Connector>('data', { required: true });

// --- STATE ---
const formRef = ref<QForm | null>(null);
const formData = ref({
  url: '',
  username: '',
  api_token: '',
  space_key: '',
  include_attachments: false,
});

// --- INIT ---
onMounted(() => {
  if (data.value.configuration) {
    const c = data.value.configuration;
    formData.value = {
      url: c.url || '',
      username: c.username || '',
      api_token: c.api_token || '',
      space_key: c.space_key || '',
      include_attachments: c.include_attachments || false,
    };
  }
});

// --- EXPOSED METHODS ---
async function submit(): Promise<boolean> {
  if (!formRef.value) return false;

  const valid = await formRef.value.validate();
  if (!valid) return false;

  // Sync back to main connector object
  if (!data.value.configuration) data.value.configuration = {};

  Object.assign(data.value.configuration, {
    url: formData.value.url,
    username: formData.value.username,
    api_token: formData.value.api_token,
    space_key: formData.value.space_key || null,
    include_attachments: formData.value.include_attachments,
  });

  return true;
}

defineExpose({ submit });
</script>
