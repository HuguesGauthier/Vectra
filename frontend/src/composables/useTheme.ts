import { ref } from 'vue';
import { Dark } from 'quasar';
import { settingsService } from 'src/services/settingsService';
import { useAuthStore } from 'src/stores/authStore';

// Global state for theme preference
const themePreference = ref<'auto' | 'dark' | 'light'>('auto');

export function useTheme() {
  const authStore = useAuthStore();

  const applyTheme = () => {
    const pref = themePreference.value;
    let isDark = true; // Default to dark

    if (pref === 'auto') {
      isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    } else if (pref === 'light') {
      isDark = false;
    } else {
      isDark = true;
    }

    // Apply Quasar Dark mode (optional, but good for some generic components)
    Dark.set(isDark);

    // Apply Custom CSS Classes
    if (isDark) {
      document.body.classList.remove('body--light');
      document.body.classList.add('body--dark'); // Optional if Quasar adds this automatically
    } else {
      document.body.classList.remove('body--dark');
      document.body.classList.add('body--light');
    }
  };

  const setParams = async (theme: 'auto' | 'dark' | 'light') => {
    themePreference.value = theme;
    applyTheme();
    // Persist to localStorage for immediate load next time
    localStorage.setItem('theme_preference', theme);

    // Persist to Backend if Admin
    if (authStore.isAdmin) {
      try {
        await settingsService.updateBatch([
          { key: 'ui_dark_mode', value: theme, group: 'general', is_secret: false },
        ]);
      } catch (e) {
        console.warn('Failed to persist theme setting', e);
      }
    }
  };

  const initTheme = async () => {
    // 1. Try to get from LocalStorage first for speed
    const stored = localStorage.getItem('theme_preference');
    if (stored && ['auto', 'dark', 'light'].includes(stored)) {
      themePreference.value = stored as 'auto' | 'dark' | 'light';
    }

    applyTheme();

    // 2. Listen for System Changes (if auto)
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (themePreference.value === 'auto') {
        applyTheme();
      }
    };
    mediaQuery.addEventListener('change', handleChange);

    // 3. If Admin/Authenticated, maybe fetch from backend global settings?
    // For now, we prioritize local preference as "Theme" is usually local.
    // If the requirement is to use the global setting from SettingsPage, we hook that up.
    // Given the prompt showed the Settings Page, we should sync with it if possible.
    if (authStore.isAdmin) {
      try {
        const settings = await settingsService.getAll();
        const themeSetting = settings.find((s) => s.key === 'ui_dark_mode');
        if (themeSetting) {
          // If backend has a value, do we overwrite local?
          // Usually local override > global default.
          // But let's sync if local is empty.
          if (!stored) {
            await setParams(themeSetting.value as 'auto' | 'dark' | 'light');
          }
        }
      } catch (e) {
        console.warn('Failed to fetch theme settings', e);
      }
    }
  };

  return {
    themePreference,
    setParams,
    initTheme,
    applyTheme,
  };
}
