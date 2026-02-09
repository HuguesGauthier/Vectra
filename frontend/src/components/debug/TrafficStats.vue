<template>
  <div class="row q-col-gutter-sm">
    <div class="col-6">
      <q-card flat class="bg-primary text-grey-5 text-center q-pa-sm col justify-center">
        <div class="text-caption text-grey-5">Total Messages</div>
        <div class="text-h6 text-accent">{{ totalMessages }}</div>
      </q-card>
    </div>
    <div class="col-6">
      <q-card
        flat
        class="bg-primary text-grey-5 text-center q-pa-sm full-height col justify-center"
      >
        <div class="text-caption text-grey-5">Msgs / sec</div>
        <div class="text-h6 text-accent">{{ messagesPerSecond }}</div>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  totalMessages: number;
  messagesPerSecond: number;
  lastMessageType: string;
}>();
</script>
