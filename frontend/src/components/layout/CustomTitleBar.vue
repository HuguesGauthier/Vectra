<template>
  <q-bar
    v-if="isElectron"
    class="bg-secondary text-white q-electron-drag custom-title-bar relative-position"
  >
    <div class="absolute-center row items-center q-electron-drag--exception">
      <q-img src="@assets/vectra_logo.png" width="18px" height="18px" />
      <div class="font-discord q-ml-sm">Vectra</div>
    </div>

    <q-space />

    <div class="row no-wrap q-electron-drag--exception">
      <q-btn dense flat square @click="minimize" class="window-control-btn">
        <svg aria-hidden="true" width="11" height="11" viewBox="0 0 11 11">
          <path d="M11 5.5H0" stroke="currentColor" stroke-width="1" />
        </svg>
      </q-btn>
      <q-btn dense flat square @click="maximize" class="window-control-btn">
        <svg aria-hidden="true" width="10" height="10" viewBox="0 0 10 10">
          <rect
            width="9"
            height="9"
            x="0.5"
            y="0.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1"
          />
        </svg>
      </q-btn>
      <q-btn dense flat square @click="close" class="window-control-btn close-btn">
        <svg aria-hidden="true" width="11" height="11" viewBox="0 0 11 11">
          <path d="M0.5 0.5L10.5 10.5M10.5 0.5L0.5 10.5" stroke="currentColor" stroke-width="1" />
        </svg>
      </q-btn>
    </div>
  </q-bar>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const isElectron = computed(() => window.electronAPI !== undefined);

async function minimize() {
  await window.electronAPI?.minimize();
}

async function maximize() {
  await window.electronAPI?.maximize();
}

async function close() {
  await window.electronAPI?.close();
}
</script>

<style scoped>
.custom-title-bar {
  height: 32px; /* Thicker than default dense, compact like Discord */
  user-select: none;
}

.font-discord {
  font-weight: bold;
  font-size: 13px;
  font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.window-control-btn {
  width: 38px;
  height: 32px;
  opacity: 0.8;
  border-radius: 0 !important;
}

.window-control-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  opacity: 1;
}

.close-btn:hover {
  background-color: #f23f42 !important; /* Discord Red */
}
</style>
