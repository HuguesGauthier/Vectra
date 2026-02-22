<template>
  <q-card
    flat
    class="user-card bg-primary column full-height clickable"
    @click="$emit('edit')"
  >
    <div class="user-card-banner">
      <div class="glow-overlay" :style="glowStyle"></div>
    </div>

    <q-card-section class="q-pt-none q-px-lg relative-position info-section">
      <!-- Overlapping Avatar -->
      <div class="avatar-wrapper">
        <div class="avatar-ring" :style="{ borderColor: statusColor }">
          <q-avatar size="80px" class="user-avatar-main shadow-5">
            <img
              v-if="user.avatar_url"
              :src="avatarUrl"
              :alt="user.email"
              :style="{
                objectFit: 'cover',
                objectPosition: `center ${user.avatar_vertical_position || 50}%`,
              }"
            />
            <div v-else class="flex flex-center full-width full-height bg-sixth text-h4 text-weight-bold">
              {{ user.email.charAt(0).toUpperCase() }}
            </div>
          </q-avatar>
        </div>
        <!-- Live Status Dot -->
        <div 
          class="status-dot shadow-2" 
          :class="{ 'status-dot--active': user.is_active, 'status-dot--inactive': !user.is_active }"
        ></div>
      </div>

      <!-- User Identification (Left Aligned) -->
      <div class="column q-mt-sm">
        <div class="text-h6 text-weight-bolder user-name">
          {{ fullName }}
        </div>
        <div class="text-caption  email-text q-mb-xs">
          {{ user.email }}
        </div>

        <!-- Job Titles Tags -->
        <div v-if="user.job_titles?.length" class="row q-gutter-xs q-mb-md">
          <q-badge
            v-for="title in user.job_titles"
            :key="title"
            color="accent"
            outline
            class="job-title-badge"
          >
            {{ title }}
          </q-badge>
        </div>
        <div v-else class="q-mb-md"></div>

        <!-- Role Badge -->
        <div class="row">
          <div class="role-badge">
            <q-icon :name="user.role === 'admin' ? 'stars' : 'person'" size="14px" class="q-mr-xs" />
            {{ user.role }}
          </div>
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { api } from 'boot/axios';

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  job_titles?: string[];
  avatar_url?: string;
  avatar_vertical_position?: number;
}

const props = defineProps<{
  user: User;
}>();

defineEmits(['edit']);

const fullName = computed(() => {
  return props.user.first_name
    ? `${props.user.first_name} ${props.user.last_name || ''}`
    : props.user.email;
});

const statusColor = computed(() => {
  return props.user.is_active ? 'var(--q-third)' : 'var(--q-grey-7)';
});

const avatarUrl = computed(() => {
  const path = props.user.avatar_url;
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('data:')) return path;

  const baseUrl = api.defaults.baseURL || '';
  const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  return `${cleanBase}${cleanPath}`;
});

const glowStyle = computed(() => {
  return {
    background: `radial-gradient(circle at 50% 0%, var(--q-accent)25 0%, transparent 70%)`
  };
});
</script>

<style scoped>
.user-card {
  border: 1px solid var(--q-sixth);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.glow-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  pointer-events: none;
  opacity: 0.6;
  transition: opacity 0.4s ease;
}

.user-card:hover {
  transform: translateY(-8px);
  border-color: var(--q-sixth);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

.user-card:hover .glow-overlay {
  opacity: 0.8;
}

.user-card-banner {
  height: 80px;
  background: linear-gradient(135deg, var(--q-secondary) 0%, var(--q-primary) 100%);
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.avatar-wrapper {
  margin-top: -40px;
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}

.avatar-ring {
  padding: 4px;
  border: 2px solid;
  border-radius: 50%;
  transition: all 0.4s ease;
  background: var(--q-primary);
}

.status-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--q-primary);
  z-index: 2;
}

.status-dot--active {
  background: #00e676;
  box-shadow: 0 0 10px rgba(0, 230, 118, 0.4);
}

.status-dot--inactive {
  background: #757575;
}

.user-card:hover .avatar-ring {
  transform: scale(1.05) rotate(2deg);
}

.info-section {
  padding-bottom: 24px;
}

.user-name {
  letter-spacing: -0.01em;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  line-height: 1.1;
}

.email-text {
  opacity: 0.5;
  font-size: 0.75rem;
}

.role-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--q-third);
  color: var(--q-text-sub);
  padding: 2px 10px;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: flex;
  align-items: center;
}

.job-title-badge {
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 4px;
  opacity: 0.8;
  border-color: rgba(var(--q-accent-rgb), 0.3);
}
</style>
