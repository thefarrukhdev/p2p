import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { UserMe } from '@/shared/types/api';
import { User, Settings, LogOut, LayoutDashboard, CalendarDays, Trophy, Shield } from 'lucide-react';

interface MobileMenuProps {
  user: UserMe;
  onClose: () => void;
  onLogout: () => void;
}

export function MobileMenu({ user, onClose, onLogout }: MobileMenuProps) {
  const { t } = useTranslation();

  return (
    <div className="lg:hidden mt-4 pt-4 border-t-2 border-gray-200 dark:border-gray-700 animate-fade-in font-montserrat">
      <div className="space-y-3">
        {/* User Info */}
        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl border-2 border-gray-900 flex items-center gap-3">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.login || user.school21_login}
              className="w-10 h-10 rounded-full object-cover border border-gray-900"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center">
              <User className="w-5 h-5 text-white" />
            </div>
          )}
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-bold text-gray-900 dark:text-white truncate">
              @{user.login || user.school21_login}
            </p>
            <p className="text-xs font-ibm-plex-mono text-gray-600 dark:text-gray-400 mt-0.5 truncate">
              {user.campus || 'Platform'} • Level {user.level || 1}
            </p>
          </div>
        </div>

        {/* Mobile Navigation Links */}
        <Link
          to="/dashboard"
          onClick={onClose}
          className="flex items-center justify-center gap-3 px-4 py-3 bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] text-white font-bold font-montserrat rounded-xl border-2 border-gray-900 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]"
        >
          <LayoutDashboard className="w-5 h-5 text-black" />
          <span className="text-black font-extrabold">{t('nav.home')}</span>
        </Link>

        <Link
          to="/slots"
          onClick={onClose}
          className="flex items-center justify-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-bold font-montserrat rounded-xl border-2 border-gray-900"
        >
          <CalendarDays className="w-5 h-5 text-[#38C9E6]" />
          {t('nav.slots')}
        </Link>

        <Link
          to="/leaderboard"
          onClick={onClose}
          className="flex items-center justify-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-bold font-montserrat rounded-xl border-2 border-gray-900"
        >
          <Trophy className="w-5 h-5 text-[#43E8A0]" />
          {t('nav.leaderboard')}
        </Link>

        <Link
          to="/profile"
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-semibold font-montserrat rounded-xl border-2 border-gray-900"
        >
          <User className="w-5 h-5 text-[#38C9E6]" />
          {t('nav.profile')}
        </Link>

        <Link
          to="/settings"
          onClick={onClose}
          className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-semibold font-montserrat rounded-xl border-2 border-gray-900"
        >
          <Settings className="w-5 h-5 text-[#43E8A0]" />
          {t('nav.settings')}
        </Link>

        {(user.is_admin || (user as any).is_superuser) && (
          <a
            href="/admin"
            target="_blank"
            rel="noreferrer"
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 text-amber-400 font-semibold font-montserrat rounded-xl border-2 border-gray-900"
          >
            <Shield className="w-5 h-5" />
            {t('nav.admin')}
          </a>
        )}

        {/* Logout */}
        <button
          onClick={() => {
            onLogout();
            onClose();
          }}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-red-500 text-white font-bold font-montserrat rounded-xl border-2 border-gray-900 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] cursor-pointer"
        >
          <LogOut className="w-5 h-5" />
          {t('nav.logout')}
        </button>
      </div>
    </div>
  );
}

export default MobileMenu;
