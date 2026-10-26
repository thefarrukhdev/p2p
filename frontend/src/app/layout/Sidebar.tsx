import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '@/features/auth/hooks';
import { Avatar, Modal } from '@/shared/ui';
import {
  LayoutDashboard,
  CalendarDays,
  Search,
  Trophy,
  User,
  Bell,
  Settings,
  LogOut,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  unreadCount?: number;
}

export function Sidebar({ unreadCount = 0 }: SidebarProps) {
  const { logout, user } = useAuth();
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  const links = [
    { to: '/dashboard', label: 'Bosh sahifa', icon: LayoutDashboard },
    { to: '/slots', label: 'Slotlarim', icon: CalendarDays },
    { to: '/search', label: 'Qidiruv', icon: Search },
    { to: '/leaderboard', label: 'Reyting', icon: Trophy },
    { to: '/profile', label: 'Profil', icon: User },
    { to: '/notifications', label: 'Bildirishnomalar', icon: Bell, badge: unreadCount },
    { to: '/settings', label: 'Sozlamalar', icon: Settings },
  ];

  return (
    <aside className="fixed top-6 bottom-6 left-6 z-30 w-[260px] hidden lg:flex flex-col bg-[#2A3442] border-2 border-black rounded-[32px] shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all duration-300 overflow-hidden">
      {/* Platform Branding Logo */}
      <div className="h-22 flex items-center gap-3 px-6 border-b-2 border-black bg-[#1E2A38]/40">
        {/* Animated logo frame */}
        <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:rotate-3 transition-transform cursor-pointer">
          <span className="text-black font-extrabold text-xs tracking-tighter font-montserrat">P2P</span>
        </div>
        <div className="flex flex-col">
          <span className="font-extrabold text-white text-base leading-tight font-montserrat tracking-tight">P2P Platform</span>
          <span className="text-[10px] text-[#38C9E6] font-ibm-plex-mono tracking-widest font-black mt-0.5">PEER LEARNING</span>
        </div>
      </div>

      {/* User profile quick widget if authenticated */}
      {user && (
        <div className="pt-5 pb-1">
          <div className="mx-4 p-3.5 bg-[#34495E] border-2 border-black rounded-2xl flex items-center gap-3 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] relative overflow-hidden group">
            <Avatar src={user.avatar_url} name={user.login || user.school21_login} size="sm" />
            <div className="flex flex-col min-w-0 flex-grow">
              <span className="text-[11px] font-black text-white truncate max-w-full tracking-tight">
                {user.first_name || user.login || user.school21_login}
              </span>
              <span className="text-[9px] text-[#38C9E6] font-black tracking-widest uppercase">
                LEVEL {user.level} {user.main_track ? `• ${user.main_track}` : ''}
              </span>
            </div>
            <div className="flex flex-col items-end text-right">
              <span className="text-[9px] font-black text-black whitespace-nowrap bg-[#43E8A0] px-1.5 py-0.5 rounded border border-black/10">
                {user.peer_points} PT
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation List */}
      <nav className="flex-1 px-4 py-4 space-y-2.5 overflow-y-auto">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `relative flex items-center justify-between rounded-xl px-4 py-3 text-xs font-bold font-montserrat tracking-wider uppercase transition-all duration-200 group border-2
                 ${
                   isActive
                     ? 'text-black bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] translate-x-[1px] translate-y-[1px]'
                     : 'text-[#B0BEC5] border-transparent hover:text-white hover:bg-gray-600/30 lg:hover:bg-[#34495E] hover:border-black hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px]'
                 }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 transition-transform group-hover:scale-110 text-current duration-150" />
                <span>{link.label}</span>
              </div>
              {link.badge && link.badge > 0 ? (
                <span className="bg-[#FF9B9B] text-black text-[10px] font-black h-5 min-w-[20px] px-1.5 rounded-lg border-2 border-black flex items-center justify-center shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] animate-pulse">
                  {link.badge}
                </span>
              ) : null}
            </NavLink>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t-2 border-black bg-[#1E2A38]/20">
        <button
          onClick={() => setIsLogoutModalOpen(true)}
          className="w-full h-11 flex items-center justify-center gap-3 rounded-xl border-2 border-black bg-[#FF9B9B] hover:bg-[#FF8888] text-black font-extrabold font-montserrat text-xs tracking-wider uppercase shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          <span>Chiqish</span>
        </button>
      </div>

      <Modal
        isOpen={isLogoutModalOpen}
        onClose={() => setIsLogoutModalOpen(false)}
        title="Tizimdan Chiqish"
      >
        <div className="flex flex-col gap-4">
          <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed">
            Haqiqatdan ham tizimdan chiqmoqchimisiz? Kelgusi kirishlar uchun qayta avtorizatsiyadan oʻtishingiz talab etiladi.
          </p>
          <div className="flex gap-3 justify-end pt-2">
            <button
              onClick={() => setIsLogoutModalOpen(false)}
              className="px-4 py-2 bg-[#34495E] hover:bg-gray-600 text-white font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
            >
              Qolish
            </button>
            <button
              onClick={() => {
                setIsLogoutModalOpen(false);
                logout();
              }}
              className="px-4 py-2 bg-[#FF9B9B] hover:bg-[#FF8888] text-black font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
            >
              Chiqish
            </button>
          </div>
        </div>
      </Modal>
    </aside>
  );
}
export default Sidebar;
