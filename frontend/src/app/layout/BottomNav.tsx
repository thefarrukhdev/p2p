import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarDays,
  Trophy,
  User,
} from 'lucide-react';

export function BottomNav() {
  const tabs = [
    { to: '/dashboard', label: 'Asosiy', icon: LayoutDashboard },
    { to: '/slots', label: 'Slotlar', icon: CalendarDays },
    { to: '/leaderboard', label: 'Reyting', icon: Trophy },
    { to: '/profile', label: 'Profil', icon: User },
  ];

  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 lg:hidden bg-[#2A3442]/95 backdrop-blur-lg flex items-center justify-around h-16 pb-[env(safe-area-inset-bottom,0px)] box-content px-2 shadow-[0_-4px_0px_0px_rgba(0,0,0,1)] border-t-2 border-black">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 text-[10px] font-bold font-montserrat tracking-tight w-16 h-full transition-all relative
               ${isActive ? 'text-[#38C9E6]' : 'text-[#B0BEC5] hover:text-[#38C9E6]'}`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute top-1 w-6 h-1 rounded-full bg-[#38C9E6] shadow-[0_0_8px_rgba(56,201,230,0.8)]" />
                )}
                <Icon className={`h-5 w-5 transition-transform ${isActive ? 'scale-110 text-[#38C9E6]' : ''}`} />
                <span className="truncate max-w-full text-[9px] uppercase font-extrabold">{tab.label}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
export default BottomNav;
