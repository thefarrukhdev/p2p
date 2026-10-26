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
    <nav className="fixed bottom-0 inset-x-0 z-40 lg:hidden bg-[#2A3442]/95 backdrop-blur-lg flex items-center justify-around h-16 pb-[env(safe-area-inset-bottom,0px)] box-content px-2 shadow-[0_-4px_0px_rgba(0,0,0,0.15)] border-t border-black/20">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 text-[10px] font-bold font-montserrat tracking-tight w-16 h-full transition-all
               ${isActive ? 'text-[#38C9E6] scale-105' : 'text-[#B0BEC5] hover:text-[#38C9E6]'}`
            }
          >
            <Icon className="h-5 w-5" />
            <span className="truncate max-w-full text-[9px] uppercase">{tab.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
export default BottomNav;
