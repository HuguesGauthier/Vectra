<template>
  <q-expansion-item
    class="pipeline-steps-block q-my-sm shadow-1"
    header-class="header-bg"
    expand-icon-class="text-primary"
  >
    <template v-slot:header>
      <div class="row items-center full-width">
        <q-icon name="route" size="sm" class="q-mr-sm text-primary" />
        <div class="text-subtitle2 text-weight-bold flex-1">
          {{ $t('pipelineSteps.title') || 'Pipeline Steps' }}
        </div>

        <!-- Summary Badges -->
        <div class="row q-gutter-x-sm q-ml-sm text-caption">
          <!-- Status Counts -->
          <div class="badge-pill bg-opacity">
            <span class="text-positive">{{ completedCount }} ✓</span>
            <span v-if="failedCount > 0" class="text-negative q-ml-xs">{{ failedCount }} ✕</span>
          </div>

          <!-- Duration -->
          <div class="badge-pill bg-opacity">
            <q-icon name="timer" size="14px" class="q-mr-xs" />
            {{ totalDuration.toFixed(2) }}s
          </div>

          <!-- Tokens -->
          <div v-if="totalInputTokens > 0 || totalOutputTokens > 0" class="badge-pill bg-opacity">
            ↑{{ totalInputTokens }} ↓{{ totalOutputTokens }}
          </div>
        </div>
      </div>
    </template>

    <q-card class="transparent-bg shadow-none">
      <q-card-section class="q-pt-none q-pb-md px-lg">
        <div
          class="steps-tree column q-ml-sm q-mt-sm"
          style="border-left: 1px solid rgba(255, 255, 255, 0.1); padding-left: 12px"
        >
          <StepNode
            v-for="(step, index) in filteredRootSteps"
            :key="step.step_id || index"
            :step="step"
            :is-last="index === filteredRootSteps.length - 1"
          />
        </div>
      </q-card-section>
    </q-card>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatStep } from '../../composables/useChatStream';

// Helper component for recursive rendering
// We declare it inline in the script setup,
// but Vue doesn't support recursive components fully inline without a name,
// so we'll just use a small scoped component definition or generate flat HTML.
// Better: We can flatten the tree and render with padding, or use a local component.

const props = defineProps<{
  steps: ChatStep[];
}>();

// --- Metrics Computation ---

const completedStep = computed(() => {
  return props.steps.find((s) => s.step_type === 'completed' && s.status === 'completed');
});

const totalDuration = computed(() => {
  if (completedStep.value) return completedStep.value.duration || 0;
  return props.steps.reduce((sum, s) => sum + (s.parent_id ? 0 : s.duration || 0), 0);
});

const totalInputTokens = computed(() => {
  if (completedStep.value) return completedStep.value.tokens?.input || 0;
  return props.steps.reduce((sum, s) => sum + (s.parent_id ? 0 : s.tokens?.input || 0), 0);
});

const totalOutputTokens = computed(() => {
  if (completedStep.value) return completedStep.value.tokens?.output || 0;
  return props.steps.reduce((sum, s) => sum + (s.parent_id ? 0 : s.tokens?.output || 0), 0);
});

const completedCount = computed(() => {
  return props.steps.filter(
    (s) => s.status === 'completed' && s.step_type !== 'completed' && !s.parent_id,
  ).length;
});

const failedCount = computed(() => {
  return props.steps.filter((s) => s.status === 'failed' && !s.parent_id).length;
});

// --- Hierarchy Reconstruction ---

const rootTree = computed(() => {
  const stepMap = new Map<string, ChatStep>();
  const roots: ChatStep[] = [];

  // Pass 1: Flatten
  const flattenToMap = (itemList: ChatStep[]) => {
    itemList.forEach((s) => {
      const copy = { ...s, sub_steps: [] as ChatStep[] };
      if (!copy.step_id) copy.step_id = `step_${Math.random()}`;
      stepMap.set(copy.step_id, copy);
      if (s.sub_steps && s.sub_steps.length > 0) {
        flattenToMap(s.sub_steps);
      }
    });
  };
  flattenToMap(props.steps);

  // Pass 2: Link
  stepMap.forEach((step) => {
    if (step.parent_id && stepMap.has(step.parent_id)) {
      const parent = stepMap.get(step.parent_id)!;
      if (!parent.sub_steps) parent.sub_steps = [];
      if (!parent.sub_steps.some((c) => c.step_id === step.step_id)) {
        parent.sub_steps.push(step);
      }
    } else {
      roots.push(step);
    }
  });

  return roots;
});

// Filter out the artificial 'completed' summary step from top level display
const filteredRootSteps = computed(() => {
  return rootTree.value.filter((s) => s.step_type !== 'completed');
});
</script>

<script lang="ts">
import { defineComponent, h } from 'vue';
import type { VNode } from 'vue';
import messages from 'src/i18n';

// Local Recursive Component for Step Nodes
const StepNode = defineComponent({
  name: 'StepNode',
  props: {
    step: { type: Object, required: true },
    level: { type: Number, default: 0 },
    isLast: { type: Boolean, default: false },
  },
  setup(props) {
    // Instead of complex render functions, we'll write a simple template block inside setup
    return (): VNode => {
      const step = props.step as ChatStep;
      const level = props.level;

      const statusIcon = step.status === 'completed' ? '✓' : step.status === 'failed' ? '✕' : '⟳';
      const statusColor =
        step.status === 'completed'
          ? 'text-positive'
          : step.status === 'failed'
            ? 'text-negative'
            : 'text-warning';

      const durationText =
        step.duration !== undefined && step.duration > 0.01 ? `${step.duration.toFixed(2)}s` : '';
      const tokensText =
        step.tokens && (step.tokens.input > 0 || step.tokens.output > 0)
          ? `↑${step.tokens.input} ↓${step.tokens.output}`
          : '';

      const locale = localStorage.getItem('app_language') || 'en-US';
      const localeMessages = (messages as any)[locale]; // eslint-disable-line @typescript-eslint/no-explicit-any
      const tooltip = localeMessages?.stepDescriptions?.[step.step_type] || step.step_type;

      // The main row
      const rowNode = h(
        'div',
        {
          class: 'row items-center no-wrap full-width q-mb-xs relative-position',
          style: {
            opacity: level > 0 ? 0.8 : 1,
            minHeight: '28px',
            fontSize: level > 0 ? '12px' : '13px',
          },
        },
        [
          // Connector lines (handled by CSS borders typically, but we use a simpler layout here)
          h(
            'div',
            { class: `q-mr-sm text-weight-bold ${statusColor}` },
            level > 0 ? `↳ ${statusIcon}` : statusIcon,
          ),

          // Label
          h(
            'div',
            {
              class: 'ellipsis flex-1 cursor-pointer',
              style: { fontWeight: level > 0 ? 400 : 500 },
              title: tooltip,
            },
            step.label,
          ),

          // Metrics (right aligned)
          h('div', { class: 'row q-gutter-x-sm text-caption text-mono opacity-80' }, [
            durationText ? h('span', { class: 'metric-badge' }, durationText) : null,
            tokensText ? h('span', { class: 'metric-badge' }, tokensText) : null,
          ]),
        ],
      );

      // Children
      let childrenNode = null;
      if (step.sub_steps && step.sub_steps.length > 0) {
        childrenNode = h('div', {
          class: 'column q-ml-md q-mt-xs',
          style: {
            borderLeft: '1px solid rgba(255,255,255,0.05)',
            paddingLeft: '12px'
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        }, (step.sub_steps || []).map((child: any, idx: number): VNode => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return h(StepNode as any, { step: child, level: level + 1, isLast: idx === (step.sub_steps?.length || 0) - 1 });
        }));
      }

      return h('div', { class: 'full-width column' }, [rowNode, childrenNode]);
    };
  },
});
</script>

<style scoped>
.pipeline-steps-block {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.header-bg {
  background: rgba(0, 0, 0, 0.2);
}

.transparent-bg {
  background: transparent !important;
}

.badge-pill {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  display: flex;
  align-items: center;
}

.bg-opacity {
  background: rgba(255, 255, 255, 0.1) !important;
}

::v-deep(.metric-badge) {
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 6px;
  display: inline-block;
}

::v-deep(.text-mono) {
  font-family: 'Courier New', Courier, monospace;
}
</style>
