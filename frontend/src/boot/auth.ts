import { boot } from 'quasar/wrappers';
import { useAuthStore } from 'stores/authStore';

export default boot(async () => {
  const authStore = useAuthStore();
  await authStore.initialize();
});
