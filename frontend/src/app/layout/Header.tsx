import { Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/hooks';
import { NotificationsBell } from '@/features/notifications';
import { Coins, Zap, Settings } from 'lucide-react';
import { Avatar } from '@/shared/ui';

interface HeaderProps {
  unreadCount?: number;
}

export function Header(_props: HeaderProps) {
  const { user } = useAuth();

  if (!user) {
    return (
      <header className="h-18 lg:h-20 border-[3px] border-black rounded-2xl lg:rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] lg:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] bg-[#2A3442] flex items-center justify-between px-3 sm:px-6 lg:px-8 sticky top-3 lg:top-6 z-20 mx-2 sm:mx-4 lg:mx-10 mt-3 lg:mt-6">
        <div className="h-6 w-32 bg-[#34495E] animate-pulse rounded-lg border-2 border-black" />
        <div className="h-10 w-10 rounded-xl bg-[#34495E] animate-pulse border-2 border-black" />
      </header>
    );
  }

  return (
    <header className="h-18 lg:h-20 border-[3px] border-black rounded-2xl lg:rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] lg:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] bg-[#2A3442]/95 backdrop-blur-md flex items-center justify-between px-2.5 sm:px-6 lg:px-8 sticky top-3 lg:top-6 z-20 mx-2 sm:mx-4 lg:mx-10 mt-3 lg:mt-6">
      {/* Greetings block */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
        {/* P2P Badge for mobile */}
        <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] lg:hidden shrink-0">
          <span className="text-black font-extrabold text-[9px] font-montserrat tracking-tighter">P2P</span>
        </div>
        <div className="flex flex-col min-w-0">
          <h2 className="text-xs sm:text-sm font-extrabold text-white font-montserrat tracking-tight leading-none truncate min-w-0">
            Xush kelibsiz, <span className="text-[#38C9E6]">@{user.login || user.school21_login}</span>
          </h2>
          <span className="text-[8px] sm:text-[10px] text-[#B0BEC5] uppercase tracking-wider font-ibm-plex-mono font-bold mt-1 truncate">
            <span className="inline sm:hidden">{user.campus ? user.campus.split(' ')[0] : 'CAMPUS'}</span>
            <span className="hidden sm:inline">PROGRAM: {user.core_program || 'CORE'} • {user.campus ? user.campus.toUpperCase() : 'CAMPUS'}</span>
          </span>
        </div>
      </div>

      {/* Stats and Profile trigger Block */}
      <div className="flex items-center gap-1 sm:gap-2.5 shrink-0 ml-1.5 sm:ml-2">
        {/* Points Display */}
        <div className="flex items-center gap-1 sm:gap-1.5 px-2 py-1 sm:px-3 sm:py-1.5 rounded-xl bg-[#34495E] border-2 border-black text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] font-ibm-plex-mono" title="Peer Points">
          <Zap className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-[#38C9E6] fill-[#38C9E6]/20" />
          <span className="text-[10px] sm:text-xs font-black">
            {user.peer_points}
            <span className="text-[9px] text-[#38C9E6] font-bold ml-0.5 hidden min-[400px]:inline"> PT</span>
          </span>
        </div>

        {/* Coins Display (hidden on very small mobile) */}
        <div className="hidden min-[380px]:flex items-center gap-1 sm:gap-1.5 px-2 py-1 sm:px-3 sm:py-1.5 rounded-xl bg-[#34495E] border-2 border-black text-[#ffd740] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] font-ibm-plex-mono" title="Peer Coins">
          <Coins className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-[#ffd740] fill-[#ffd740]/20" />
          <span className="text-[10px] sm:text-xs font-black">
            {user.peer_coins}
            <span className="text-[9px] text-[#ffd740] font-bold ml-0.5 hidden min-[440px]:inline"> COIN</span>
          </span>
        </div>

        {/* Notification Bell dropdown */}
        <div className="flex items-center justify-center p-1 sm:p-2 rounded-xl bg-[#34495E] text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <NotificationsBell className="text-[#B0BEC5] hover:text-white" />
        </div>

        {/* Settings button redirect on mobile (hidden on ultra-small screens, accessible via bottom nav) */}
        <Link
          to="/settings"
          className="hidden min-[420px]:flex items-center justify-center p-1.5 sm:p-2 min-h-[36px] min-w-[36px] rounded-xl bg-[#34495E] hover:bg-gray-600 text-white border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] transition-all cursor-pointer lg:hidden"
          aria-label="Sozlamalar"
        >
          <Settings className="h-4 w-4 sm:h-4.5 sm:w-4.5 text-[#B0BEC5]" />
        </Link>

        {/* User avatar directly linking to /profile */}
        <Link to="/profile" className="flex items-center justify-center p-0.5 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] transition-all hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
          <Avatar src={user.avatar_url} name={user.login || user.school21_login} size="sm" className="rounded-lg h-7 w-7 sm:h-8 sm:w-8" />
        </Link>
      </div>
    </header>
  );
}
export default Header;
