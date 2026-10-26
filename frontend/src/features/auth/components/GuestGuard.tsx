import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';
import { ReactNode } from 'react';

interface GuestGuardProps {
  children: ReactNode;
}

export function GuestGuard({ children }: GuestGuardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const onboardingDone = useAuthStore((s) => s.onboardingDone);
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string; search?: string } })?.from;
  const redirectTarget = from ? `${from.pathname}${from.search || ''}` : '/dashboard';

  if (isAuthenticated) {
    if (!onboardingDone) {
      return <Navigate to="/onboarding" replace />;
    }
    return <Navigate to={redirectTarget} replace />;
  }

  return children;
}
export default GuestGuard;
