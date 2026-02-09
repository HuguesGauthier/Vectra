<template>
  <q-input
    outlined
    v-model="model"
    :label="label"
    readonly
    class="cursor-pointer"
    @click="pickFolder"
  >
    <template v-slot:append>
      <q-btn flat round dense icon="folder_open" @click.stop="pickFolder">
        <AppTooltip>
          {{ isElectron ? $t('browseFolder') : $t('manualInputRequired') }}
        </AppTooltip>
      </q-btn>
    </template>
  </q-input>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuasar } from 'quasar';
import { useNotification } from 'src/composables/useNotification';
import { useI18n } from 'vue-i18n';
import AppTooltip from 'components/common/AppTooltip.vue';

// --- PROPS & MODEL ---
defineProps<{
  label?: string;
}>();

const model = defineModel<string>({ required: false });
const $q = useQuasar();
const { notifyError } = useNotification();
const { t } = useI18n();

// --- STATE ---
const isElectron = computed(() => {
  return window.electronAPI !== undefined;
});

// --- FUNCTIONS ---
async function pickFolder() {
  if (isElectron.value && window.electronAPI) {
    try {
      const path = await window.electronAPI.selectFolder();
      if (path) {
        model.value = path;
      }
    } catch (error) {
      console.error('Failed to pick folder:', error);
      notifyError('Failed to access folder picker.');
    }
  } else {
    // Web Mode Fallback
    $q.dialog({
      title: t('manualInputRequiredTitle'),
      message: t('manualInputPastePath'),
      prompt: {
        model: model.value || '',
        type: 'text',
      },
      cancel: true,
      persistent: true,
    }).onOk((data: string) => {
      model.value = data;
    });
  }
}
</script>
