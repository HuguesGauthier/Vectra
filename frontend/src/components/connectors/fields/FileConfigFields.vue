<template>
  <div class="q-gutter-md">
    <div class="text-subtitle2 text-grey-5 q-mb-xs q-mt-lg">{{ $t('fileConfiguration') }}</div>
    <div class="text-caption text-grey-6">
      {{ $t('fileUploadOnlyHint') }}
    </div>

    <q-file
      v-if="file !== undefined"
      v-model="file"
      :label="$t('selectFile')"
      standout
      color="white"
      bottom-slots
      counter
      :rules="[(val) => !!val || (config.path ? true : $t('fileRequired'))]"
    >
      <template v-slot:prepend>
        <q-icon name="attach_file" />
      </template>
      <template v-slot:append>
        <q-icon name="close" @click.stop.prevent="file = null" class="cursor-pointer" />
      </template>
      <template v-slot:hint v-if="!file && config.path">
        <div class="text-grey-5">
          <q-icon name="check_circle" color="positive" size="xs" class="q-mr-xs" />
          {{ $t('fileAlreadyUploaded') }}: {{ getFileName(config.path) }}
        </div>
      </template>
    </q-file>
  </div>
</template>

<script setup lang="ts">
// --- DEFINITIONS ---
// File connector has no specific configuration fields, but needs internal index sig
type FileConfig = Record<string, unknown>;

const config = defineModel<FileConfig>({ required: true });
const file = defineModel<File | null>('file');

function getFileName(path: unknown): string {
  if (typeof path !== 'string') return '';
  return path.split(/[/\\]/).pop() || '';
}
</script>
