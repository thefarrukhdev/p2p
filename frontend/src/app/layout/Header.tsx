import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/features/auth/hooks';
import { NotificationsBell } from '@/features/notifications';
import { Coins, Zap } from 'lucide-react';
import { Avatar, LanguageSwitcher } from '@/shared/ui';

interface HeaderProps {
  unreadCount?: number;
}

export function Header(_props: HeaderProps) {
  const { t } = useTranslation();
  const { user } = useAuth();

  if (!user) {
    return (
      <header className="h-14 sm:h-16 lg:h-20 border-[3px] border-black rounded-2xl lg:rounded-3xl shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] lg:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] bg-[#2A3442] flex items-center justify-between px-3 sm:px-6 lg:px-8 sticky top-3 lg:top-6 z-20 mx-2 sm:mx-4 lg:mx-10 mt-3 lg:mt-6">
        <div className="h-6 w-24 sm:w-32 bg-[#34495E] animate-pulse rounded-lg border-2 border-black" />
        <div className="h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-[#34495E] animate-pulse border-2 border-black" />
      </header>
    );
  }

  return (
    <header className="h-14 sm:h-16 lg:h-20 border-[3px] border-black rounded-2xl lg:rounded-3xl shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] lg:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] bg-[#2A3442]/95 backdrop-blur-md flex items-center justify-between px-3 sm:px-6 lg:px-8 sticky top-3 lg:top-6 z-20 mx-2 sm:mx-4 lg:mx-10 mt-3 lg:mt-6">
      {/* Greetings block */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
        {/* P2P Badge for mobile */}
        <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] lg:hidden shrink-0">
          <span className="text-black font-extrabold text-[9px] font-montserrat tracking-tighter">P2P</span>
        </div>
        <div className="flex flex-col min-w-0">
          <h2 className="text-xs sm:text-sm font-extrabold text-white font-montserrat tracking-tight leading-none truncate min-w-0">
            <span className="hidden sm:inline">{t('nav.welcome', 'Xush kelibsiz')}, </span>
            <span className="text-[#38C9E6]">@{user.login || user.school21_login}</span>
          </h2>
          <span className="text-[8px] sm:text-[10px] text-[#B0BEC5] uppercase tracking-wider font-ibm-plex-mono font-bold mt-1 truncate">
            <span className="inline sm:hidden">{user.campus ? user.campus.split(' ')[0] : 'CAMPUS'}</span>
            <span className="hidden sm:inline">{user.core_program || 'CORE'} • {user.campus ? user.campus.toUpperCase() : 'CAMPUS'}</span>
          </span>
        </div>
      </div>

      {/* Stats and Profile trigger Block */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0 ml-1.5 sm:ml-2">
        {/* Points Display */}
        <div className="flex items-center gap-1 sm:gap-1.5 px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-xl bg-[#34495E] border-2 border-black text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] font-ibm-plex-mono shrink-0" title="Peer Points">
          <Zap className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-[#38C9E6] fill-[#38C9E6]/20" />
          <span className="text-[10px] sm:text-xs font-black">
            {user.peer_points}
            <span className="text-[9px] text-[#38C9E6] font-bold ml-0.5">PT</span>
          </span>
        </div>

        {/* Coins Display (hidden on mobile, shown on sm+) */}
        <div className="hidden sm:flex items-center gap-1 sm:gap-1.5 px-2.5 py-1.5 rounded-xl bg-[#34495E] border-2 border-black text-[#ffd740] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] font-ibm-plex-mono shrink-0" title="Peer Coins">
          <Coins className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-[#ffd740] fill-[#ffd740]/20" />
          <span className="text-xs font-black">
            {user.peer_coins}
            <span className="text-[9px] text-[#ffd740] font-bold ml-0.5"> COIN</span>
          </span>
        </div>

        {/* Mobile Language Switcher */}
        <LanguageSwitcher />

        {/* Notification Bell dropdown */}
        <div className="flex items-center justify-center rounded-xl bg-[#34495E] text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] shrink-0">
          <NotificationsBell className="text-[#B0BEC5] hover:text-white" />
        </div>

        {/* User avatar directly linking to /profile */}
        <Link
          to="/profile"
          className="shrink-0 flex items-center justify-center rounded-full hover:scale-105 active:scale-95 transition-transform"
          aria-label={t('nav.profile')}
        >
          <Avatar
            src={user.avatar_url}
            name={user.login || user.school21_login}
            size="sm"
            className="shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
          />
        </Link>
      </div>
    </header>
  );
}
export default Header;
