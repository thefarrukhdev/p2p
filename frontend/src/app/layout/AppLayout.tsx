import { Outlet } from 'react-router-dom';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import { useDashboard } from '@/features/dashboard/hooks';
import { Navbar, Header, BottomNav } from '.';
import { DotField } from '@/shared/ui';

export function AppLayout() {
  // Bind global WebSocket real-time updates automatically when layout mounts
  useWebSocket();

  // Query unread notifications counts to feed to layouts
  const { dashboard } = useDashboard();
  const unreadCount = dashboard?.unread_notifications || 0;

  return (
    <div className="min-h-screen bg-[#1E2A38] text-white flex flex-col font-ibm-plex-mono relative overflow-x-hidden">
      {/* Dynamic Senior Interactive Global Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <DotField
          dotRadius={1.5}
          dotSpacing={14}
          bulgeStrength={67}
          glowRadius={160}
          sparkle={false}
          waveAmplitude={0}
          cursorRadius={500}
          cursorForce={0.1}
          bulgeOnly
          gradientFrom="rgba(56, 201, 230, 0.25)"
          gradientTo="rgba(67, 232, 160, 0.18)"
          glowColor="rgba(56, 201, 230, 0.1)"
        />
      </div>

      {/* Unified Desktop Top Navbar */}
      <Navbar unreadCount={unreadCount} />

      {/* Content wrapper */}
      <div className="flex flex-col flex-grow relative z-10">
        {/* Mobile only header */}
        <div className="lg:hidden">
          <Header unreadCount={unreadCount} />
        </div>

        <main className="flex-grow p-3.5 sm:p-6 lg:px-10 lg:py-8 pb-36 lg:pb-8 max-w-[1440px] w-full mx-auto relative z-10">
          <Outlet />
        </main>
      </div>

      {/* Mobile navigation tab bar */}
      <BottomNav />
    </div>
  );
}
export default AppLayout;
