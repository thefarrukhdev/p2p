import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  onboardingDone: boolean;
  setTokens: (accessToken: string, refreshToken: string, onboardingDone: boolean) => void;
  setOnboardingDone: (onboardingDone: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      onboardingDone: false,
      setTokens: (accessToken, refreshToken, onboardingDone) =>
        set({
          accessToken,
          refreshToken,
          isAuthenticated: true,
          onboardingDone,
        }),
      setOnboardingDone: (onboardingDone) => set({ onboardingDone }),
      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          onboardingDone: false,
        }),
    }),
    {
      name: 'peer-learn-auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        onboardingDone: state.onboardingDone,
      }),
    }
  )
);

// Cross-tab authentication synchronization
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === 'peer-learn-auth-storage') {
      if (!e.newValue) {
        useAuthStore.getState().logout();
      } else {
        try {
          const parsed = JSON.parse(e.newValue);
          if (parsed?.state && !parsed.state.isAuthenticated) {
            useAuthStore.getState().logout();
          }
        } catch {
          // Ignore JSON parse errors
        }
      }
    }
  });
}
