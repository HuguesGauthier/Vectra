<template>
  <q-dialog v-model="isOpen" persistent position="right" maximized>
    <q-card style="width: 50vh; background-color: var(--q-fifth)">
      <q-card-section>
        <div class="text-h6">{{ isEditing ? $t('editUser') : $t('addUser') }}</div>
      </q-card-section>

      <q-card-section>
        <!-- Avatar Upload Section -->
        <div class="column items-center q-mb-md">
          <div class="avatar-container" @mousedown="startDrag" @touchstart="startDrag">
            <q-avatar size="100px" :color="formData.avatar_url ? 'transparent' : 'grey-7'">
              <img
                v-if="formData.avatar_url"
                :src="
                  formData.avatar_url.startsWith('data:')
                    ? formData.avatar_url
                    : `http://localhost:8000/api/v1${formData.avatar_url}`
                "
                :style="{
                  objectFit: 'cover',
                  objectPosition: `center ${formData.avatar_vertical_position}%`,
                  pointerEvents: 'none',
                  userSelect: 'none',
                }"
              />
              <q-icon v-else name="person" size="60px" color="grey-4" />
            </q-avatar>

            <!-- Drag hint overlay -->
            <div v-if="formData.avatar_url" class="drag-hint">
              <q-icon name="drag_indicator" size="20px" color="white" style="opacity: 0.7" />
            </div>
          </div>

          <q-file
            v-model="avatarFile"
            accept="image/*"
            @update:model-value="handleAvatarChange"
            max-file-size="2097152"
            class="q-mt-sm"
            dense
            outlined
            bg-color="primary"
            style="max-width: 250px"
          >
            <template v-slot:prepend>
              <q-icon name="photo_camera" />
            </template>
            <template v-slot:hint>
              {{ $t('maxFileSize', { size: '2MB' }) }}
            </template>
          </q-file>

          <!-- Position indicator -->
          <div v-if="formData.avatar_url" class="text-caption text-grey-6 q-mt-xs">
            {{ $t('dragToPosition') }}
          </div>

          <q-btn
            v-if="formData.avatar_url"
            flat
            dense
            size="sm"
            color="negative"
            class="q-mt-xs"
            @click="removeAvatar"
          >
            {{ $t('removePhoto') }}
          </q-btn>
        </div>
      </q-card-section>

      <q-card-section>
        <q-form ref="formRef" @submit.prevent="handleSubmit" class="q-gutter-md">
          <q-input
            v-model="formData.email"
            :label="$t('email')"
            outlined
            color="accent"
            bg-color="primary"
            lazy-rules
            :rules="emailRules"
          />

          <q-input
            v-model="formData.first_name"
            :label="$t('firstName')"
            outlined
            color="accent"
            bg-color="primary"
          />

          <q-input
            v-model="formData.last_name"
            :label="$t('lastName')"
            outlined
            color="accent"
            bg-color="primary"
          />

          <q-input
            v-model="formData.password"
            :label="isEditing ? $t('newPasswordOptional') : $t('password')"
            type="password"
            outlined
            color="accent"
            bg-color="primary"
            :rules="passwordRules"
          />

          <q-select
            v-model="formData.role"
            :options="roleOptions"
            :label="$t('role')"
            outlined
            color="accent"
            options-cover
            emit-value
            map-options
            bg-color="primary"
            popup-content-class="custom-select-popup"
          />

          <q-toggle
            v-model="formData.is_active"
            :label="$t('isActive')"
            color="accent"
            keep-color
            :disable="isEditingSelf"
          >
            <AppTooltip v-if="isEditingSelf">{{ $t('cannotDeactivateSelf') }}</AppTooltip>
          </q-toggle>

          <div class="row justify-end q-mt-md q-gutter-x-sm">
            <q-btn :label="$t('cancel')" color="grey" flat @click="handleCancel" />
            <q-btn :label="$t('save')" type="submit" color="accent" unelevated />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type QForm } from 'quasar';
import { api } from 'boot/axios';
import AppTooltip from 'components/common/AppTooltip.vue';

// --- TYPES ---
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  avatar_url?: string;
  avatar_vertical_position?: number;
}

export interface UserFormData {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role: string;
  is_active: boolean;
  avatar_url?: string;
  avatar_vertical_position: number;
}

interface Props {
  modelValue: boolean;
  userToEdit?: User | null;
  existingUsers?: User[];
  currentUserEmail?: string;
}

// --- PROPS ---
const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  userToEdit: null,
  existingUsers: () => [],
  currentUserEmail: '',
});

// --- EMITS ---
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  save: [data: Partial<UserFormData>];
  cancel: [];
}>();

// --- STATE ---
const { t } = useI18n();

const formData = ref<UserFormData>({
  id: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  role: 'user',
  is_active: true,
  avatar_url: '',
  avatar_vertical_position: 50,
});

const avatarFile = ref<File | null>(null);
const formRef = ref<QForm | null>(null);

const roleOptions = [
  { label: 'User', value: 'user' },
  { label: 'Admin', value: 'admin' },
];

// --- COMPUTED ---
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const isEditing = computed(() => !!props.userToEdit);

const isEditingSelf = computed(
  () => isEditing.value && props.userToEdit?.email === props.currentUserEmail,
);

const emailRules = computed(() => [
  (val: string) => !!val || t('fieldRequired'),
  (val: string) => /.+@.+\..+/.test(val) || t('invalidEmailArguments'),
  (val: string) => {
    const existingUser = props.existingUsers.find(
      (u) => u.email === val && u.id !== formData.value.id,
    );
    return !existingUser || t('emailAlreadyExists');
  },
]);

const passwordRules = computed(() =>
  isEditing.value ? [] : [(val: string) => !!val || t('fieldRequired')],
);

// --- WATCHERS ---
watch(
  () => props.userToEdit,
  (user) => {
    if (user) {
      formData.value = {
        id: user.id,
        email: user.email,
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        password: '',
        role: user.role,
        is_active: user.is_active,
        avatar_url: user.avatar_url || '',
        avatar_vertical_position: user.avatar_vertical_position || 50,
      };
      avatarFile.value = null;
    } else {
      resetForm();
    }
  },
  { immediate: true },
);

// --- FUNCTIONS ---
function resetForm() {
  formData.value = {
    id: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    role: 'user',
    is_active: true,
    avatar_url: '',
    avatar_vertical_position: 50,
  };
  avatarFile.value = null;
}

function handleAvatarChange(file: File | null) {
  if (!file) {
    formData.value.avatar_url = '';
    return;
  }

  // Validate file type
  if (!file.type.startsWith('image/')) {
    formData.value.avatar_url = '';
    avatarFile.value = null;
    return;
  }

  // Create preview URL
  const reader = new FileReader();
  reader.onload = (e) => {
    formData.value.avatar_url = e.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function removeAvatar() {
  formData.value.avatar_url = '';
  formData.value.avatar_vertical_position = 50;
  avatarFile.value = null; // This should trigger the q-file to clear/reset
}

// Drag to position avatar
let isDragging = false;
let startY = 0;
let startPosition = 50;

function startDrag(e: MouseEvent | TouchEvent) {
  if (!formData.value.avatar_url) return;

  isDragging = true;
  startY = 'touches' in e && e.touches[0] ? e.touches[0].clientY : (e as MouseEvent).clientY;
  startPosition = formData.value.avatar_vertical_position;

  // Add event listeners
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.addEventListener('touchmove', onDrag);
  document.addEventListener('touchend', stopDrag);

  e.preventDefault();
}

function onDrag(e: MouseEvent | TouchEvent) {
  if (!isDragging) return;

  const currentY =
    'touches' in e && e.touches[0] ? e.touches[0].clientY : (e as MouseEvent).clientY;
  const deltaY = currentY - startY;

  // Convert pixels to percentage (100px avatar height)
  const deltaPercent = (deltaY / 100) * 100;

  // Update position (inverted: drag down = move image up in view)
  let newPosition = startPosition - deltaPercent;
  newPosition = Math.max(0, Math.min(100, newPosition));

  formData.value.avatar_vertical_position = Math.round(newPosition);
}

function stopDrag() {
  isDragging = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('touchmove', onDrag);
  document.removeEventListener('touchend', stopDrag);
}

async function handleSubmit() {
  if (!formRef.value) return;

  const valid = await formRef.value.validate();
  if (!valid) return;

  try {
    let avatarUrl = formData.value.avatar_url || '';

    // Upload avatar if editing and a new file was selected
    if (props.userToEdit?.id && avatarFile.value) {
      avatarUrl = await uploadAvatar(props.userToEdit.id);
    }

    // Prepare data for save
    const dataToSave: Record<string, unknown> = {
      email: formData.value.email,
      first_name: formData.value.first_name,
      last_name: formData.value.last_name,
      role: formData.value.role,
      is_active: formData.value.is_active,
      avatar_url: avatarUrl,
      avatar_vertical_position: formData.value.avatar_vertical_position,
    };

    // For new users, pass the avatar file so parent can upload after user is created
    if (!props.userToEdit && avatarFile.value) {
      dataToSave.avatarFile = avatarFile.value;
    }

    if (props.userToEdit) {
      dataToSave.id = formData.value.id;
      if (formData.value.password) {
        dataToSave.password = formData.value.password;
      }
    } else {
      dataToSave.password = formData.value.password;
    }

    emit('save', dataToSave);
  } catch (error) {
    console.error('Failed to submit form:', error);
  }
}

async function uploadAvatar(userId: string): Promise<string> {
  if (!avatarFile.value) return '';

  try {
    const formDataUpload = new FormData();
    formDataUpload.append('file', avatarFile.value);

    const response = await api.post(`/users/${userId}/avatar`, formDataUpload, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data.avatar_url || '';
  } catch (error) {
    console.error('Failed to upload avatar:', error);
    throw error;
  }
}

function handleCancel() {
  emit('cancel');
  isOpen.value = false;
}
</script>

<style scoped>
/* Avatar container for dragging */
.avatar-container {
  position: relative;
  display: inline-block;
  border-radius: 50%;
  transition: all 0.2s;
  cursor: move;
}

.avatar-container:hover .drag-hint {
  opacity: 1;
}

.drag-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
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

<style>
/* Global styles for q-select popup (rendered in portal, needs non-scoped) */
.custom-select-popup {
  background-color: var(--q-primary) !important;
}

.custom-select-popup .q-item {
  color: var(--q-text-main);
}

.custom-select-popup .q-item__label {
  color: var(--q-text-main);
}

.custom-select-popup .q-item:hover {
  background-color: var(--q-third) !important;
}

.custom-select-popup .q-item--active {
  background-color: var(--q-accent) !important;
  color: white;
}
</style>
