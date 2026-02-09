<template>
  <div class="trending-list-container">
    <!-- Loading State -->
    <div v-if="loading" class="q-pa-md">
      <q-item v-for="n in limit" :key="n" class="q-px-none">
        <q-item-section avatar>
          <q-skeleton type="circle" size="32px" />
        </q-item-section>
        <q-item-section>
          <q-skeleton type="text" width="60%" />
          <q-skeleton type="text" width="40%" class="text-caption" />
        </q-item-section>
      </q-item>
    </div>

    <!-- Empty State -->
    <div v-else-if="topics.length === 0" class="flex flex-center column q-pa-lg text-grey-5">
      <q-icon name="trending_up" size="48px" class="q-mb-sm opacity-50" />
      <div class="text-caption">{{ $t('noTrendsYet') || 'No trending topics yet' }}</div>
    </div>

    <!-- List Content -->
    <q-list v-else padding>
      <q-item
        v-for="(topic, index) in topics"
        :key="topic.id"
        :clickable="interactive"
        :v-ripple="interactive"
        @click="handleSelect(topic)"
        class="topic-item q-mb-xs rounded-borders"
        :class="{ 'cursor-pointer': interactive }"
      >
        <!-- Rank Icon -->
        <q-item-section avatar>
          <div class="relative-position flex flex-center" style="width: 32px; height: 32px">
            <!-- Top 3 Styling -->
            <template v-if="index < 3">
              <q-icon
                :name="index === 0 ? 'local_fire_department' : 'emoji_events'"
                size="24px"
                :color="getRankColor(index)"
              />
              <q-badge
                v-if="index === 0"
                floating
                color="red"
                rounded
                style="top: -4px; right: -4px; width: 8px; height: 8px; padding: 0"
              />
            </template>
            <!-- Rank 4+ -->
            <span v-else class="text-weight-bold text-grey-6 text-h6" style="font-size: 14px">
              {{ index + 1 }}
            </span>
          </div>
        </q-item-section>

        <!-- Topic Text -->
        <q-item-section>
          <q-item-label :class="{ 'text-weight-bold': index < 3 }" class="text-body2">
            {{ topic.canonical_text }}
          </q-item-label>
          <q-item-label caption class="text-grey-5 text-xs">
            {{ topic.frequency }} {{ $t('requests') || 'requests' }}
          </q-item-label>
        </q-item-section>

        <!-- Action Icon (if interactive) -->
        <q-item-section side v-if="interactive">
          <q-icon name="chevron_right" size="xs" color="grey-7" />
        </q-item-section>
      </q-item>
    </q-list>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { trendingService, type TrendingTopic } from 'src/services/trendingService';

const props = defineProps({
  assistantId: {
    type: String,
    default: null,
  },
  limit: {
    type: Number,
    default: 10,
  },
  interactive: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['select']);

const topics = ref<TrendingTopic[]>([]);
const loading = ref(true);

// Rank Colors
const getRankColor = (index: number) => {
  switch (index) {
    case 0:
      return 'amber-9'; // Gold
    case 1:
      return 'grey-4'; // Silver
    case 2:
      return 'brown-5'; // Bronze
    default:
      return 'grey-7';
  }
};

const fetchTopics = async () => {
  loading.value = true;
  try {
    topics.value = await trendingService.getTrendingTopics(props.assistantId, props.limit);
  } catch (err) {
    console.error('Failed to load trending topics:', err);
  } finally {
    loading.value = false;
  }
};

const handleSelect = (topic: TrendingTopic) => {
  if (props.interactive) {
    emit('select', topic.canonical_text);
  }
};

onMounted(() => {
  void fetchTopics();
});

// Refetch if assistantId changes (e.g. switching assistants in chat)
watch(
  () => props.assistantId,
  () => {
    void fetchTopics();
  },
);
</script>

<style lang="scss" scoped>
@import 'src/css/quasar.variables.scss';

.topic-item {
  transition: background-color 0.2s;
  border: 1px solid transparent;

  &:hover {
    background-color: $third;
    border-color: rgba(255, 255, 255, 0.1);
  }
}

.opacity-50 {
  opacity: 0.5;
}

.text-xs {
  font-size: 11px;
}
</style>
