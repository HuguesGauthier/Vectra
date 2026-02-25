import { defineStore } from 'pinia';
import { api } from 'boot/axios';
import { jwtDecode } from 'jwt-decode';

interface User {
  id: string;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  avatar_vertical_position?: number;
}

interface AuthState {
  token: string | null;
  user: User | null;
}

interface JwtPayload {
  exp: number;
  sub: string;
  // add other fields if used
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => {
    const token = localStorage.getItem('token');
    return {
      token: token || null,
      user: null,
    };
  },

  getters: {
    isAuthenticated: (state) => {
      if (!state.token) return false;
      try {
        const decoded = jwtDecode<JwtPayload>(state.token);
        const currentTime = Date.now() / 1000;
        return decoded.exp > currentTime;
      } catch {
        return false;
      }
    },
    isAdmin: (state) => {
      return state.user?.role === 'admin';
    },
  },

  actions: {
    async login(email: string, password: string) {
      try {
        const params = new URLSearchParams();
        params.append('username', email);
        params.append('password', password);

        const response = await api.post('/auth/login', params, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });

        const token = response.data.access_token;
        console.log('[AuthStore] Login Success. Token received:', token.substring(0, 10) + '...');
        this.token = token;
        localStorage.setItem('token', token);
        console.log('[AuthStore] Token saved to localStorage.');

        // Configure default header
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

        // Fetch user data
        await this.fetchUser();

        return true;
      } catch (error) {
        console.error('Login failed', error);
        throw error;
      }
    },

    async fetchUser() {
      try {
        const response = await api.get('/users/me');
        this.user = response.data;
      } catch (error) {
        console.error('Failed to fetch user', error);
        // If fetch fails (e.g. 401), we might want to logout
        // But the interceptor might handle the 401 redirect already.
        // potentially throwing here is fine or handling silent fail
      }
    },

    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];

      // Optional: Redirect to login if using router here,
      // but usually the calling component handles redirect or the global 401 guard does
    },

    async initialize() {
      if (this.token) {
        // Validate token expiry
        try {
          const decoded = jwtDecode<JwtPayload>(this.token);
          const currentTime = Date.now() / 1000;

          if (decoded.exp < currentTime) {
            // Token expired
            console.warn('Token expired, logging out');
            this.logout();
            return;
          }

          // Valid token, set header
          api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;

          // Refresh user data
          await this.fetchUser();
        } catch (e) {
          // Invalid token format
          console.error('Invalid token format', e);
          this.logout();
        }
      }
    },
  },
});
