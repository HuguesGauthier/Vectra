<template>
  <q-page class="bg-primary q-pa-lg">
    <!-- Header -->
    <div class="row items-center justify-between q-pt-md q-pb-md q-pl-none q-mb-md">
      <div>
        <div class="text-h4 text-weight-bold">{{ $t('users') }}</div>
        <div class="text-subtitle1 q-pt-xs">{{ $t('manageAppConfiguration') }}</div>
      </div>
    </div>

    <!-- Users Table -->
    <AppTable
      :rows="users"
      :columns="columns"
      row-key="id"
      :loading="loading"
      v-model:filter="filter"
      :pagination="{ sortBy: 'full_name', descending: false, rowsPerPage: 0 }"
      no-data-icon="group"
      :no-data-title="$t('noUsersFound')"
      :no-data-message="$t('addFirstUser')"
    >
      <!-- Add button -->
      <template #add-button>
        <q-btn color="accent" icon="add" size="12px" round unelevated @click="openDialog()">
          <AppTooltip>{{ $t('addUser') }}</AppTooltip>
        </q-btn>
      </template>

      <!-- Custom row rendering -->
      <template #body="{ props }">
        <q-tr :props="props">
          <!-- Avatar Column -->
          <q-td key="avatar" :props="props" auto-width>
            <q-avatar
              size="sm"
              :color="props.row.is_active ? 'positive' : 'grey'"
              text-color="white"
            >
              <img
                v-if="props.row.avatar_url"
                :src="getAvatarUrl(props.row.avatar_url)"
                :alt="props.row.email"
                :style="{
                  objectFit: 'cover',
                  objectPosition: `center ${props.row.avatar_vertical_position || 50}%`,
                }"
              />
              <template v-else>
                {{ props.row.email.charAt(0).toUpperCase() }}
              </template>
            </q-avatar>
          </q-td>

          <!-- Full Name Column -->
          <q-td key="full_name" :props="props">
            <div
              class="text-weight-bold cursor-pointer hover-underline"
              @click="openDialog(props.row)"
            >
              {{
                props.row.first_name
                  ? `${props.row.first_name} ${props.row.last_name || ''}`
                  : props.row.email
              }}
            </div>
          </q-td>

          <!-- Email Column -->
          <q-td key="email" :props="props">
            <div>
              {{ props.row.email }}
            </div>
          </q-td>

          <!-- Role Column -->
          <q-td key="role" :props="props">
            {{ props.row.role }}
          </q-td>

          <!-- Is Active Column -->
          <q-td key="is_active" :props="props">
            <q-chip
              :color="props.row.is_active ? 'positive' : 'grey'"
              text-color="secondary"
              size="sm"
              dense
              class="q-ma-none q-pl-sm q-pr-sm"
            >
              {{ props.row.is_active ? $t('statusActive') : $t('statusInactive') }}
            </q-chip>
          </q-td>

          <!-- Actions Column -->
          <q-td key="actions" :props="props">
            <div class="row items-center q-gutter-x-sm justify-end">
              <q-btn round flat dense size="sm" icon="edit" @click="openDialog(props.row)">
                <AppTooltip>{{ $t('edit') }}</AppTooltip>
              </q-btn>
              <q-btn
                round
                flat
                dense
                size="sm"
                icon="delete"
                color="negative"
                @click="confirmDelete(props.row)"
                v-if="props.row.email !== 'admin' && props.row.email !== 'admin@vectra.ai'"
              >
                <AppTooltip>{{ $t('delete') }}</AppTooltip>
              </q-btn>
            </div>
          </q-td>
        </q-tr>
      </template>

      <!-- No data action -->
      <template #no-data-action>
        <q-btn color="accent" size="12px" icon="add" round unelevated @click="openDialog()" />
      </template>
    </AppTable>

    <!-- User Form Dialog -->
    <UserFormDialog
      v-model="dialogVisible"
      :user-to-edit="editingUser"
      :existing-users="users"
      :current-user-email="(authStore.user?.email as string) || ''"
      @save="handleSave"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from 'boot/axios';
import { useI18n } from 'vue-i18n';
import { type QTableColumn } from 'quasar';
import { useNotification } from 'src/composables/useNotification';
import { useDialog } from 'src/composables/useDialog';
import AppTooltip from 'components/common/AppTooltip.vue';
import AppTable from 'components/common/AppTable.vue';
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
  is_active: boolean;
  role: string;
  avatar_url?: string;
  avatar_vertical_position?: number;
}

// --- STATE ---
const users = ref<User[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editingUser = ref<User | null>(null);
const filter = ref('');

const columns: QTableColumn[] = [
  {
    name: 'avatar',
    label: '',
    field: 'email',
    align: 'center',
    sortable: false,
    style: 'width: 50px',
  },
  {
    name: 'full_name',
    label: t('name'),
    field: (row: User) => (row.first_name ? `${row.first_name} ${row.last_name || ''}` : row.email),
    align: 'left',
    sortable: true,
    headerStyle: 'color: var(--q-text-main)',
    style: 'color: var(--q-text-main)',
  },
  {
    name: 'email',
    label: t('email'),
    field: 'email',
    align: 'left',
    sortable: true,
    headerStyle: 'color: var(--q-text-main)',
    style: 'color: var(--q-text-main)',
  },
  {
    name: 'role',
    label: t('role'),
    field: 'role',
    align: 'left',
    sortable: true,
    headerStyle: 'color: var(--q-text-main)',
    style: 'color: var(--q-text-main)',
  },
  {
    name: 'is_active',
    label: t('status'),
    field: 'is_active',
    align: 'left',
    sortable: true,
    headerStyle: 'color: var(--q-text-main)',
    style: 'color: var(--q-text-main)',
  },
  {
    name: 'actions',
    label: t('actions'),
    field: 'actions',
    align: 'right',
    headerStyle: 'color: var(--q-text-main)',
    style: 'color: var(--q-text-main)',
  },
];

// --- FUNCTIONS ---

const getAvatarUrl = (path: string) => {
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('data:')) return path;

  // Use config base URL (e.g. /api/v1) or fallback
  const baseUrl = api.defaults.baseURL || '';
  const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  return `${cleanBase}${cleanPath}`;
};

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
.hover-underline:hover {
  text-decoration: underline;
}
</style>
