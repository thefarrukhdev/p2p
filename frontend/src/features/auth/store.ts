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
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        onboardingDone: state.onboardingDone,
      }),
    }
  )
);
