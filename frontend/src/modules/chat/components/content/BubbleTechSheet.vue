<template>
  <div class="row justify-start q-mb-sm q-mt-lg">
    <q-expansion-item
      dense-toggle
      class="bg-transparent rounded-borders overflow-hidden full-width tech-sheet-expansion"
      header-class="q-px-none q-py-xs"
      header-style="min-height: unset"
      :expand-icon-class="`text-[${metadataTextColor}]`"
      style="border-radius: 10px"
      v-model="expanded"
    >
      <template v-slot:header>
        <div
          class="row items-center full-width"
          :style="{ color: assistant?.avatar_text_color || 'white' }"
        >
          <q-icon
            name="description"
            class="q-pl-sm q-pr-sm"
            :size="chatStore.fontSize + 4 + 'px'"
          />
          <div :style="{ fontSize: chatStore.fontSize + 'px' }">
            {{ data.title }}
          </div>
        </div>
      </template>

      <div class="q-pa-md bg-transparent">
        <!-- Relevance Text -->
        <div
          v-if="data.relevance?.text"
          class="q-mb-md"
          :style="{ fontSize: chatStore.fontSize + 'px' }"
        >
          <q-icon name="info" size="xs" class="q-mr-xs" />
          {{ data.relevance.text }}
        </div>

        <!-- Specifications Table -->
        <div v-if="data.specifications && data.specifications.length > 0">
          <div
            class="text-weight-bold q-mb-xs"
            :style="{
              fontSize: chatStore.fontSize + 'px',
              color: assistant?.avatar_text_color || 'white',
            }"
          >
            Technical Specifications
          </div>
          <q-markup-table
            flat
            dense
            bordered
            class="bg-transparent q-mb-md"
            :style="{ color: assistant?.avatar_text_color || 'white' }"
          >
            <tbody>
              <tr v-for="(spec, idx) in data.specifications" :key="idx">
                <td
                  class="text-weight-bold"
                  style="width: 40%"
                  :style="{ fontSize: chatStore.fontSize + 'px' }"
                >
                  {{ spec.label }}
                </td>
                <td :style="{ fontSize: chatStore.fontSize + 'px' }">{{ spec.value }}</td>
              </tr>
            </tbody>
          </q-markup-table>
        </div>

        <!-- Description -->
        <div v-if="data.description">
          <div
            class="text-weight-bold q-mb-xs"
            :style="{
              fontSize: chatStore.fontSize + 'px',
              color: assistant?.avatar_text_color || 'white',
            }"
          >
            Product Description
          </div>
          <div
            class=""
            style="white-space: pre-wrap"
            :style="{
              fontSize: chatStore.fontSize + 'px',
              color: assistant?.avatar_text_color || 'white',
            }"
          >
            {{ data.description }}
          </div>
        </div>

        <!-- Notes -->
        <div
          v-if="data.notes"
          class="q-mt-md q-pa-sm bg-warning text-dark rounded-borders"
          :style="{ fontSize: chatStore.fontSize - 1 + 'px' }"
        >
          <strong>Note:</strong> {{ data.notes }}
        </div>
      </div>
    </q-expansion-item>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { usePublicChatStore } from 'src/stores/publicChatStore';
import type { Assistant } from 'src/services/assistantService';

const chatStore = usePublicChatStore();

interface TechSheetData {
  title: string;
  relevance?: { text: string };
  specifications?: { label: string; value: string }[];
  description?: string;
  notes?: string;
}

const props = defineProps<{
  data: TechSheetData;
  assistant: Assistant | null;
}>();

const expanded = ref(false); // Default to collapsed for cleaner UI

const metadataTextColor = computed(() => {
  const baseColor = props.assistant?.avatar_text_color || 'white';
  return lightenColor(baseColor, 30);
});

// Helper for color (duplicated from parent for now)
function lightenColor(color: string, percent: number): string {
  const namedColors: Record<string, string> = {
    white: '#ffffff',
    black: '#000000',
    red: '#ff0000',
    green: '#00ff00',
    blue: '#0000ff',
    yellow: '#ffff00',
    cyan: '#00ffff',
    magenta: '#ff00ff',
  };

  let workingColor = color.toLowerCase();
  const namedColor = namedColors[workingColor];
  if (namedColor) workingColor = namedColor;

  if (workingColor.startsWith('#')) {
    const hex = workingColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const amount = percent / 100;
    const newR = Math.floor(r + (255 - r) * amount);
    const newG = Math.floor(g + (255 - g) * amount);
    const newB = Math.floor(b + (255 - b) * amount);

    return `rgba(${newR}, ${newG}, ${newB}, 1)`;
  }
  return color;
}
</script>
