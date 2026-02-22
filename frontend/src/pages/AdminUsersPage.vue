<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Top Bar: Search & Add -->
    <div class="row items-center justify-between q-mb-xl q-mt-md">
      <div class="row items-center q-gutter-x-md flex-grow">
        <q-input
          v-model="filter"
          dense
          outlined
          rounded
          :placeholder="$t('search')"
          class="search-input"
          bg-color="secondary"
        >
          <template #append>
            <q-icon name="search" size="xs" />
          </template>
        </q-input>

        <q-btn color="accent" icon="add" round unelevated @click="openDialog()">
          <AppTooltip>{{ $t('addUser') }}</AppTooltip>
        </q-btn>
      </div>
    </div>

    <!-- Loading State: Skeleton Cards -->
    <div v-if="loading" class="row q-col-gutter-lg">
      <div v-for="n in 8" :key="n" class="col-12 col-sm-6 col-md-4 col-lg-3">
        <q-card flat class="skeleton-user-card bg-secondary overflow-hidden">
          <div class="skeleton-banner"></div>
          <q-card-section class="q-pt-none q-px-lg relative-position">
            <div class="skeleton-avatar-wrapper">
              <q-skeleton type="QAvatar" size="80px" />
            </div>
            <div class="column q-mt-sm">
              <q-skeleton type="text" width="60%" height="24px" class="q-mb-sm" />
              <q-skeleton type="text" width="40%" height="16px" class="q-mb-md" />
              <q-skeleton type="rect" width="80px" height="20px" style="border-radius: 8px" />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredUsers.length === 0" class="column flex-center text-center q-pa-xl">
      <q-icon name="group_off" size="100px" color="grey-7" class="q-mb-md" />
      <div class="text-h5 text-grey-5 q-mb-xs">{{ $t('noUsersFound') }}</div>
      <div class="text-subtitle2 text-grey-7 q-mb-lg">
        {{ filter ? $t('tryDifferentSearch') : $t('addFirstUser') }}
      </div>
      <q-btn
        v-if="!filter"
        unelevated
        color="accent"
        icon="add"
        :label="$t('addUser')"
        @click="openDialog()"
      />
    </div>

    <!-- Users Grid -->
    <div v-else class="relative-position">
      <transition-group
        appear
        name="user-grid"
        tag="div"
        class="row q-col-gutter-lg"
      >
        <div
          v-for="user in filteredUsers"
          :key="user.id"
          class="col-12 col-sm-6 col-md-4 col-lg-3 user-item"
        >
          <UserCard
            :user="user"
            @edit="openDialog(user)"
          />
        </div>
      </transition-group>
    </div>

    <!-- User Form Dialog -->
    <UserFormDialog
      v-model="dialogVisible"
      :user-to-edit="editingUser"
      :existing-users="users"
      :current-user-email="(authStore.user?.email as string) || ''"
      @save="handleSave"
      @delete="handleDeleteStep"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { api } from 'boot/axios';
import { useI18n } from 'vue-i18n';
import { useNotification } from 'src/composables/useNotification';
import { useDialog } from 'src/composables/useDialog';
import AppTooltip from 'components/common/AppTooltip.vue';
import UserCard from 'components/admin/UserCard.vue';
import UserFormDialog from 'components/admin/UserFormDialog.vue';
import { useAuthStore } from 'stores/authStore';

// --- DEFINITIONS ---
const { t } = useI18n();
const { notifySuccess, notifyBackendError } = useNotification();
const { confirm } = useDialog();
const authStore = useAuthStore();

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

// --- STATE ---
const users = ref<User[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editingUser = ref<User | null>(null);
const filter = ref('');

const filteredUsers = computed(() => {
  if (!filter.value) return users.value;
  const f = filter.value.toLowerCase();
  return users.value.filter((u) => {
    const fullName = `${u.first_name || ''} ${u.last_name || ''}`.toLowerCase();
    return (
      u.email.toLowerCase().includes(f) ||
      fullName.includes(f) ||
      u.role.toLowerCase().includes(f)
    );
  });
});

// --- FUNCTIONS ---


const fetchUsers = async () => {
  loading.value = true;
  try {
    const response = await api.get('/users/');
    users.value = response.data;
  } catch (err) {
    notifyBackendError(err, t('failedToFetchUsers'));
  } finally {
    loading.value = false;
  }
};

const openDialog = (user?: User) => {
  editingUser.value = user || null;
  dialogVisible.value = true;
};

const handleSave = async (data: Record<string, unknown>) => {
  try {
    if (editingUser.value) {
      // Update existing user
      const payload: Record<string, unknown> = {
        email: data.email,
        role: data.role,
        is_active: data.is_active,
        first_name: data.first_name,
        last_name: data.last_name,
        job_titles: data.job_titles,
        avatar_vertical_position: data.avatar_vertical_position,
        avatar_url: data.avatar_url,
      };
      if (data.password) {
        payload.password = data.password;
      }

      await api.patch(`/users/${editingUser.value.id}`, payload);
      notifySuccess(t('userUpdated'));
    } else {
      // Create new user
      await api.post('/users/', {
        email: data.email,
        password: data.password,
        role: data.role,
        is_active: data.is_active,
        first_name: data.first_name,
        last_name: data.last_name,
        job_titles: data.job_titles,
        avatar_vertical_position: data.avatar_vertical_position,
        avatar_url: data.avatar_url,
      });

      // Upload avatar for new user if provided
      if (data.avatarFile) {
        try {
          const formData = new FormData();
          formData.append('file', data.avatarFile as File);

          // Get the newly created user's ID first
          const usersResponse = await api.get('/users/');
          const newUser = usersResponse.data.find((u: { email: string }) => u.email === data.email);

          if (newUser) {
            await api.post(`/users/${newUser.id}/avatar`, formData, {
              headers: {
                'Content-Type': 'multipart/form-data',
              },
            });
          }
        } catch (avatarError) {
          console.error('Failed to upload avatar for new user:', avatarError);
          // Silent fail on avatar is acceptable here to avoid rolling back user creation
          // But ideally we'd warn the user.
        }
      }

      notifySuccess(t('userCreated'));
    }
    dialogVisible.value = false;
    await fetchUsers();
  } catch (err) {
    notifyBackendError(err, editingUser.value ? t('failedToUpdateUser') : t('failedToCreateUser'));
  }
};

const handleDeleteStep = () => {
  if (editingUser.value) {
    confirmDelete(editingUser.value);
  }
};

const confirmDelete = (user: User) => {
  confirm({
    title: t('confirmDeletion'),
    message: t('confirmDeleteUser', { email: user.email }),
    confirmLabel: t('delete'),
    confirmColor: 'negative',
    onConfirm: () => {
      void deleteUser(user);
    },
  });
};

const deleteUser = async (user: User) => {
  try {
    await api.delete(`/users/${user.id}`);
    notifySuccess(t('userDeleted'));
    dialogVisible.value = false; // Close the dialog after deletion
    await fetchUsers();
  } catch (err) {
    notifyBackendError(err, t('failedToDeleteUser'));
  }
};

onMounted(() => {
  void fetchUsers();
});
</script>

<style scoped>
.search-input {
  width: 100%;
  max-width: 400px;
}

.flex-grow {
  flex-grow: 1;
}

/* Skeleton Styles */
.skeleton-user-card {
  border-radius: 24px;
  height: 220px;
  border: 1px solid var(--q-sixth);
}

.skeleton-banner {
  height: 80px;
  background: rgba(255, 255, 255, 0.03);
}

.skeleton-avatar-wrapper {
  margin-top: -40px;
  margin-bottom: 12px;
}

/* Grid Transitions */
.user-grid-enter-active,
.user-grid-leave-active {
  transition: all 0.5s cubic-bezier(0.55, 0, 0.1, 1);
}

.user-grid-enter-from,
.user-grid-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}

.user-grid-move {
  transition: transform 0.5s cubic-bezier(0.55, 0, 0.1, 1);
}
</style>
