import { NavLink, Link } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/features/auth/hooks';
import { NotificationsBell } from '@/features/notifications';
import { Modal, LanguageSwitcher } from '@/shared/ui';
import {
  LayoutDashboard,
  CalendarDays,
  Trophy,
  User,
  Settings,
  LogOut,
  Zap,
  ChevronDown,
} from 'lucide-react';

interface NavbarProps {
  unreadCount?: number;
}

export function Navbar(_props: NavbarProps) {
  const { t } = useTranslation();
  const { logout, user } = useAuth();
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const links = [
    { to: '/dashboard', label: t('nav.home'), icon: LayoutDashboard },
    { to: '/slots', label: t('nav.slots'), icon: CalendarDays },
    { to: '/leaderboard', label: t('nav.leaderboard'), icon: Trophy },
    { to: '/profile', label: t('nav.profile'), icon: User },
    { to: '/settings', label: t('nav.settings'), icon: Settings },
  ];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    if (isDropdownOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isDropdownOpen]);

  if (!user) {
    return (
      <nav className="h-16 hidden lg:flex items-center justify-between rounded-2xl bg-[#2A3442] border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] px-6 sticky top-6 z-30 mx-10 mt-6 font-ibm-plex-mono">
        <div className="h-6 w-32 bg-[#34495E] animate-pulse rounded-lg" />
        <div className="h-10 w-10 rounded-xl bg-[#34495E] animate-pulse" />
      </nav>
    );
  }

  return (
    <div className="hidden lg:block sticky top-6 z-30 mx-10 mt-6 font-ibm-plex-mono">
      <nav className="h-16 flex items-center justify-between rounded-2xl bg-[#2A3442] border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] px-6 relative z-30">
        {/* Logo / brand */}
        <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0 select-none cursor-pointer" title={t('nav.home')}>
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] flex items-center justify-center">
            <Zap className="h-5 w-5 text-black" />
          </div>
          <span className="text-base font-black text-white font-montserrat tracking-tight hidden xl:block">
            P2P Corpus
          </span>
        </Link>

        {/* Nav tabs */}
        <div className="flex items-center gap-1 z-20 h-full">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 h-10 rounded-xl text-[13px] font-extrabold tracking-wide font-montserrat transition-all duration-150 select-none cursor-pointer border-2
                   ${
                     isActive
                       ? 'bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] text-black border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                       : 'text-[#B0BEC5] border-transparent hover:text-white hover:bg-[#34495E]'
                   }`
                }
              >
                <Icon className="h-4 w-4" />
                <span className="hidden xl:block">{link.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 shrink-0 z-20">
          {/* Peer points */}
          <div
            className="hidden xl:flex items-center gap-1.5 px-3 h-10 rounded-xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] select-none"
            title={`${user.peer_points} Peer Points • ${user.peer_coins} Peer Coins`}
          >
            <Zap className="h-4 w-4 text-[#38C9E6]" />
            <span className="text-xs font-black text-white font-ibm-plex-mono">{user.peer_points}</span>
          </div>

          {/* Language Switcher */}
          <LanguageSwitcher />

          {/* Notifications dropdown */}
          <div className="h-10 w-10 flex items-center justify-center bg-[#34495E] rounded-xl border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
            <NotificationsBell className="text-[#B0BEC5] hover:text-white" />
          </div>

          {/* Profile dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen((v) => !v)}
              className="h-10 pl-1.5 pr-2.5 bg-[#34495E] rounded-xl flex items-center gap-1.5 text-[#B0BEC5] hover:text-white transition-all cursor-pointer border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] select-none"
              title={`@${user.login || user.school21_login}`}
            >
              <div className="h-7 w-7 rounded-lg bg-[#1E2A38] overflow-hidden flex items-center justify-center border-2 border-black">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.login || user.school21_login} className="h-full w-full object-cover" referrerPolicy="no-referrer" />
                ) : (
                  <User className="h-4 w-4 text-[#B0BEC5]" />
                )}
              </div>
              <ChevronDown className="h-4 w-4" />
            </button>

            {isDropdownOpen && (
              <div className="absolute right-0 mt-3 w-52 bg-[#2A3442] border-2 border-black rounded-2xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] py-1.5 z-50 animate-zoom-in text-sm font-bold overflow-hidden">
                <Link
                  to="/profile"
                  onClick={() => setIsDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[#B0BEC5] hover:text-white hover:bg-[#34495E] transition-all cursor-pointer"
                >
                  <User className="h-4 w-4" /> {t('nav.myProfile')}
                </Link>
                <Link
                  to="/settings"
                  onClick={() => setIsDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[#B0BEC5] hover:text-white hover:bg-[#34495E] transition-all cursor-pointer"
                >
                  <Settings className="h-4 w-4" /> {t('nav.settings')}
                </Link>
                <div className="border-t-2 border-black/40 my-1" />
                <button
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsLogoutModalOpen(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-[#FF9B9B] hover:text-white hover:bg-[#FF9B9B]/20 transition-all cursor-pointer text-left"
                >
                  <LogOut className="h-4 w-4" /> {t('nav.logout')}
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Logout confirmation */}
      <Modal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} title={t('nav.logoutConfirmTitle')}>
        <div className="flex flex-col gap-4">
          <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed">
            {t('nav.logoutConfirmDesc')}
          </p>
          <div className="flex gap-3 justify-end pt-2">
            <button
              onClick={() => setIsLogoutModalOpen(false)}
              className="px-4 h-10 bg-[#34495E] hover:bg-[#3f5870] text-white font-black rounded-xl border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all text-xs tracking-wider uppercase cursor-pointer font-montserrat"
            >
              {t('nav.stay')}
            </button>
            <button
              onClick={() => {
                setIsLogoutModalOpen(false);
                logout();
              }}
              className="px-4 h-10 bg-[#FF9B9B] hover:bg-[#ff8888] text-black font-black rounded-xl border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all text-xs tracking-wider uppercase cursor-pointer font-montserrat"
            >
              {t('nav.logout')}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Navbar;
