<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs q-mt-lg">{{ $t('sqlConfiguration') }}</div>

    <q-input
      :model-value="modelValue.host"
      @update:model-value="updateField('host', $event)"
      :label="$t('labelHost')"
      hint="localhost or IP address"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.port"
      @update:model-value="updateField('port', Number($event))"
      :label="$t('labelPort')"
      type="number"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.database"
      @update:model-value="updateField('database', $event)"
      :label="$t('labelDatabase')"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.schema"
      @update:model-value="updateField('schema', $event)"
      :label="$t('labelSchema')"
      :hint="$t('labelSchemaHint')"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.user"
      @update:model-value="updateField('user', $event)"
      :label="$t('labelUser')"
      dark
      color="white"
      standout
      lazy-rules
      :rules="[(val) => !!val || $t('fieldRequired')]"
    />

    <q-input
      :model-value="modelValue.password"
      @update:model-value="updateField('password', $event)"
      :label="$t('labelPassword')"
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
interface SqlConfig {
  host: string;
  port: number;
  database: string;
  schema: string;
  user: string;
  password: string;
}

const modelValue = defineModel<SqlConfig>({ required: true });

// --- FUNCTIONS ---
function updateField(field: keyof SqlConfig, value: string | number | null) {
  if (field === 'port') {
    modelValue.value = { ...modelValue.value, [field]: Number(value) || 5432 };
  } else {
    modelValue.value = { ...modelValue.value, [field]: String(value || '') };
  }
}
</script>
