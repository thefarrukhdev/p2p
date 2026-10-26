import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/app/layout';
import { AuthGuard, GuestGuard } from '@/features/auth/components';
import { RootRouteError } from '@/app/ErrorBoundary';
import { Spinner } from '@/shared/ui';

// Lazy-loaded views (konsolidatsiyadan keyin: 8 sahifa)
const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const OnboardingPage = lazy(() => import('@/features/onboarding/pages/OnboardingPage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const SlotsPage = lazy(() => import('@/features/slots/pages/SlotsPage'));
const SlotDetailPage = lazy(() => import('@/features/slots/pages/SlotDetailPage'));
const LeaderboardPage = lazy(() => import('@/features/leaderboard/pages/LeaderboardPage'));
const NotificationsPage = lazy(() => import('@/features/notifications/pages/NotificationsPage'));
const ProfilePage = lazy(() => import('@/features/profile/pages/ProfilePage'));
const SettingsPage = lazy(() => import('@/features/settings/pages/SettingsPage'));
const NotFoundPage = lazy(() => import('@/app/NotFoundPage'));

// High-contrast page suspense loader
const PageSuspense = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<Spinner fullScreen />}>{children}</Suspense>
);

export const router = createBrowserRouter([
  // Guest-only area
  {
    path: '/login',
    errorElement: <RootRouteError />,
    element: (
      <GuestGuard>
        <PageSuspense>
          <LoginPage />
        </PageSuspense>
      </GuestGuard>
    ),
  },

  // Onboarding area (protected)
  {
    path: '/onboarding',
    errorElement: <RootRouteError />,
    element: (
      <AuthGuard>
        <PageSuspense>
          <OnboardingPage />
        </PageSuspense>
      </AuthGuard>
    ),
  },

  // Authenticated workspace with global layout
  {
    path: '/',
    errorElement: <RootRouteError />,
    element: (
      <AuthGuard>
        <AppLayout />
      </AuthGuard>
    ),
    children: [
      { path: '', element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: (
          <PageSuspense>
            <DashboardPage />
          </PageSuspense>
        ),
      },
      {
        // Slots — "Mening slotlarim" + "Qidiruv" tab (Search shu yerga birlashtirilgan)
        path: 'slots',
        element: (
          <PageSuspense>
            <SlotsPage />
          </PageSuspense>
        ),
      },
      {
        // SlotDetail — Review shu yerda modal orqali
        path: 'slots/:id',
        element: (
          <PageSuspense>
            <SlotDetailPage />
          </PageSuspense>
        ),
      },
      {
        path: 'leaderboard',
        element: (
          <PageSuspense>
            <LeaderboardPage />
          </PageSuspense>
        ),
      },
      {
        path: 'notifications',
        element: (
          <PageSuspense>
            <NotificationsPage />
          </PageSuspense>
        ),
      },
      {
        // Profile — o'z profili
        path: 'profile',
        element: (
          <PageSuspense>
            <ProfilePage />
          </PageSuspense>
        ),
      },
      {
        // Profile — boshqa foydalanuvchi (UserProfile shu yerga birlashtirilgan)
        path: 'profile/:username',
        element: (
          <PageSuspense>
            <ProfilePage />
          </PageSuspense>
        ),
      },
      {
        path: 'settings',
        element: (
          <PageSuspense>
            <SettingsPage />
          </PageSuspense>
        ),
      },
    ],
  },

  // 404 Fallback page
  {
    path: '*',
    errorElement: <RootRouteError />,
    element: (
      <PageSuspense>
        <NotFoundPage />
      </PageSuspense>
    ),
  },
]);
export default router;
