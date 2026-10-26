import { useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { UserMe } from '@/shared/types/api';
import { User, LogOut, Settings, LayoutDashboard, Shield } from 'lucide-react';
import { Avatar } from '@/shared/ui';

interface ProfileMenuProps {
  user: UserMe;
  onLogout: () => void;
}

export function ProfileMenu({ user, onLogout }: ProfileMenuProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [hideTimeout, setHideTimeout] = useState<NodeJS.Timeout | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();

  const isProfilePage = location.pathname.startsWith('/profile');

  const userLogin = user.login || user.school21_login;
  const displayName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || userLogin;
  const username = `@${userLogin}`;

  const handleMouseEnter = () => {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      setHideTimeout(null);
    }
    setShowMenu(true);
  };

  const handleMouseLeave = () => {
    const timeout = setTimeout(() => {
      setShowMenu(false);
    }, 800);
    setHideTimeout(timeout);
  };

  const handleMenuClick = (path: string) => {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
    }
    navigate(path);
    setShowMenu(false);
  };

  const handleLogout = () => {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
    }
    setShowMenu(false);
    onLogout();
  };

  return (
    <div
      className="relative font-montserrat"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Gradient border wrapper matching CareerHub */}
      <div
        className={`rounded-full p-[2px] transition-all duration-300 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
          isProfilePage
            ? 'bg-gradient-to-br from-[#43E8A0] to-[#38C9E6]'
            : 'bg-gray-900 hover:bg-gradient-to-br hover:from-[#43E8A0] hover:to-[#38C9E6]'
        }`}
      >
        <button
          onClick={() => handleMenuClick('/profile')}
          className="w-10 h-10 rounded-full bg-white dark:bg-gray-800 transition-all flex items-center justify-center overflow-hidden cursor-pointer"
          aria-label={t('nav.profile')}
        >
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={displayName}
              className="w-full h-full object-cover"
              referrerPolicy="no-referrer"
            />
          ) : (
            <Avatar name={userLogin} size="sm" className="w-full h-full" />
          )}
        </button>
      </div>

      {showMenu && (
        <div className="absolute right-0 mt-2 w-64 bg-white/95 dark:bg-[#2A3442]/95 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 z-50 overflow-hidden animate-zoom-in">
          {/* Profile Header */}
          <div className="p-3.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full p-[2px] bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] shrink-0">
                <div className="w-full h-full rounded-full overflow-hidden bg-white dark:bg-[#1E2A38]">
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={displayName}
                      className="w-full h-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-semibold font-montserrat text-gray-900 dark:text-white truncate">
                  {displayName}
                </p>
                <p className="text-xs mt-0.5 font-ibm-plex-mono truncate text-transparent bg-clip-text bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] font-semibold">
                  {username}
                </p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <button
              onClick={() => handleMenuClick('/dashboard')}
              className="w-full px-4 py-2.5 text-left text-sm font-medium font-montserrat text-gray-700 dark:text-gray-300 hover:bg-gradient-to-r hover:from-[#38C9E6]/10 hover:to-[#43E8A0]/10 hover:text-gray-900 dark:hover:text-white flex items-center gap-3 transition-all duration-200 cursor-pointer"
            >
              <LayoutDashboard className="w-4 h-4 text-[#38C9E6]" />
              {t('nav.home')}
            </button>
            <button
              onClick={() => handleMenuClick('/profile')}
              className="w-full px-4 py-2.5 text-left text-sm font-medium font-montserrat text-gray-700 dark:text-gray-300 hover:bg-gradient-to-r hover:from-[#38C9E6]/10 hover:to-[#43E8A0]/10 hover:text-gray-900 dark:hover:text-white flex items-center gap-3 transition-all duration-200 cursor-pointer"
            >
              <User className="w-4 h-4 text-[#43E8A0]" />
              {t('nav.profile')}
            </button>
            <button
              onClick={() => handleMenuClick('/settings')}
              className="w-full px-4 py-2.5 text-left text-sm font-medium font-montserrat text-gray-700 dark:text-gray-300 hover:bg-gradient-to-r hover:from-[#38C9E6]/10 hover:to-[#43E8A0]/10 hover:text-gray-900 dark:hover:text-white flex items-center gap-3 transition-all duration-200 cursor-pointer"
            >
              <Settings className="w-4 h-4 text-[#38C9E6]" />
              {t('nav.settings')}
            </button>

            {(user.is_admin || (user as any).is_superuser) && (
              <a
                href="/admin"
                target="_blank"
                rel="noreferrer"
                className="w-full px-4 py-2.5 text-left text-sm font-medium font-montserrat text-amber-400 hover:bg-amber-400/10 flex items-center gap-3 transition-all duration-200 cursor-pointer"
              >
                <Shield className="w-4 h-4" />
                {t('nav.admin')}
              </a>
            )}

            {/* Divider */}
            <div className="my-1 border-t border-gray-200 dark:border-gray-700" />

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2.5 text-left text-sm font-semibold font-montserrat text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3 transition-all duration-200 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              {t('nav.logout')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileMenu;
