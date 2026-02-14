<template>
  <div class="row justify-center max-width-container">
    <div class="col-12 col-md-8 col-lg-6">
      <!-- Trigger Card -->
      <q-card
        class="selection-card cursor-pointer q-pa-lg relative-position bg-secondary"
        v-ripple
        @click="isOpen = true"
      >
        <q-card-section class="column items-center text-center">
          <div v-if="selectedTypeData">
            <q-avatar
              :color="selectedTypeData.color"
              :text-color="selectedTypeData.textColor"
              size="80px"
              :icon="selectedTypeData.icon"
              class="q-mb-md shadow-1"
            />
            <div class="text-h5">{{ selectedTypeData.name }}</div>
            <div class="text-subtitle1 text-grey-5 q-mt-sm">
              {{ selectedTypeData.description }}
            </div>
            <div class="text-caption text-accent q-mt-md">
              {{ $t('clickToChange') }}
            </div>
          </div>
          <div v-else>
            <q-avatar color="accent" size="80px" icon="add_link" class="q-mb-md shadow-1" />
            <div class="text-h5">{{ $t('selectConnectorType') }}</div>
            <div class="text-subtitle1 text-grey-5 q-mt-sm">
              {{ $t('clickToBrowseConnectors') }}
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>

    <!-- Selection Dialog -->
    <q-dialog v-model="isOpen">
      <q-card class="bg-primary var(--q-text-main) column full-height" style="min-width: 68vw">
        <!-- Dialog Header -->
        <div
          class="q-pa-md bg-secondary border-bottom row items-center justify-between sticky-top z-top"
        >
          <div class="text-h6">{{ $t('selectConnectorType') }}</div>
          <q-btn flat round dense icon="close" v-close-popup />
        </div>

        <div class="col scroll q-pa-lg relative-position hide-scrollbar">
          <!-- Search Bar -->
          <div class="q-mb-xl q-mt-md max-width-container q-mx-auto">
            <q-input
              v-model="searchQuery"
              outlined
              :placeholder="$t('searchConnectors')"
              color="accent"
              bg-color="secondary"
              class="search-input"
            >
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
              <template v-slot:append v-if="searchQuery">
                <q-icon name="close" @click="searchQuery = ''" class="cursor-pointer" />
              </template>
            </q-input>
          </div>

          <!-- Grid -->
          <div class="row q-col-gutter-lg justify-center">
            <div
              v-for="type in filteredTypes"
              :key="type.id"
              class="col-12 col-sm-6 col-md-4 col-lg-3"
            >
              <q-card
                class="selection-card cursor-pointer full-height q-pa-sm bg-secondary"
                :class="{ selected: modelValue === type.id }"
                v-ripple
                @click="selectType(type.id)"
              >
                <q-card-section class="column items-center text-center">
                  <q-avatar
                    :color="type.color"
                    :text-color="type.textColor"
                    size="60px"
                    :icon="type.icon"
                    class="q-mb-md shadow-1"
                  />
                  <div class="text-h6 var(--q-text-main)">{{ type.name }}</div>
                  <div class="text-caption text-grey-5 q-mt-sm text-center ellipsis-2-lines">
                    {{ type.description }}
                  </div>
                </q-card-section>
                <div v-if="modelValue === type.id" class="selected-overlay">
                  <q-icon name="check_circle" color="accent" size="28px" />
                </div>
              </q-card>
            </div>
          </div>

          <!-- No Results -->
          <div v-if="filteredTypes.length === 0" class="text-center q-mt-xl text-grey-5">
            <q-icon name="search_off" size="64px" class="q-mb-md opacity-50" />
            <div class="text-h6">{{ $t('noConnectorsFound') }}</div>
            <p>{{ $t('tryAdjustingSearch') }}</p>
          </div>
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

defineOptions({
  name: 'ConnectorTypeStep',
});

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const { t } = useI18n();

// State
const isOpen = ref(false);
const searchQuery = ref('');

// Standard connector types
const connectorTypes = computed(() => [
  {
    id: 'local_file',
    name: t('csvFile'),
    description: t('csvFileDesc'),
    icon: 'file_upload',
    color: 'grey-9',
    textColor: 'white',
  },
  {
    id: 'local_folder',
    name: t('networkName'),
    description: t('networkDesc'),
    icon: 'folder',
    color: 'amber-9',
    textColor: 'white',
  },
  // {
  //   id: 'confluence',
  //   name: t('confluence'),
  //   description: t('confluenceDesc'),
  //   icon: 'img:https://cdn.worldvectorlogo.com/logos/confluence-1.svg',
  //   color: 'blue-5',
  //   textColor: 'white',
  // },
  // {
  //   id: 'sharepoint',
  //   name: t('sharePoint'),
  //   description: t('sharePointDesc'),
  //   icon: 'cloud_circle',
  //   color: 'teal-6',
  //   textColor: 'white',
  // },
  {
    id: 'sql',
    name: t('sql'),
    description: t('sqlDesc'),
    icon: 'storage',
    color: 'blue-9',
    textColor: 'white',
  },
]);

// Computed
const selectedTypeData = computed(() => {
  return connectorTypes.value.find((c) => c.id === props.modelValue);
});

const filteredTypes = computed(() => {
  if (!searchQuery.value) return connectorTypes.value;
  const query = searchQuery.value.toLowerCase();
  return connectorTypes.value.filter(
    (type) =>
      type.name.toLowerCase().includes(query) || type.description.toLowerCase().includes(query),
  );
});

// Methods
function selectType(id: string) {
  emit('update:modelValue', id);
  isOpen.value = false;
  searchQuery.value = '';
}
</script>

<style scoped>
.selection-card {
  transition: all 0.2s ease-in-out;
  border: 1px solid transparent;
  background: var(--q-primary);
  border-radius: 16px;
}

.selection-card:hover {
  transform: translateY(-4px);
  background: var(--q-secondary);
  border-color: var(--q-third);
}

.selection-card.selected {
  border-color: var(--q-accent);
  background: var(--q-secondary);
}

.selected-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  animation: fadeIn 0.2s ease-out;
}

.max-width-dialog {
  max-width: 1200px;
  width: 100%;
}

.sticky-top {
  position: sticky;
  top: 0;
}

.z-top {
  z-index: 1000;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Input field borders */
:deep(.q-field--outlined .q-field__control):before {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined .q-field__control):after {
  border-color: var(--q-sixth) !important;
  border-width: 1px !important;
}

:deep(.q-field--outlined.q-field--focused .q-field__control):after {
  border-color: var(--q-accent) !important;
  border-width: 1px !important;
}
</style>
