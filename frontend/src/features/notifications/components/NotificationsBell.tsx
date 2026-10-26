import { useEffect, useRef, useState } from 'react';
import { useNotifications } from '@/features/notifications/hooks';
import { formatRelativeTime } from '@/shared/lib/utils';
import { Bell, CheckSquare, Sparkles, BookOpen, AlertCircle, Check } from 'lucide-react';

interface NotificationsBellProps {
  /** Bell ikonka klass (rang) */
  className?: string;
}

function getNotificationIcon(type: string) {
  switch (type) {
    case 'slot_booked':
      return <BookOpen className="h-4 w-4 text-[#38C9E6]" />;
    case 'slot_started':
      return <Sparkles className="h-4 w-4 text-[#ffd740]" />;
    case 'slot_completed':
      return <CheckSquare className="h-4 w-4 text-[#43E8A0]" />;
    default:
      return <Bell className="h-4 w-4 text-[#B0BEC5]" />;
  }
}

/**
 * Bildirishnomalar qo'ng'irog'i + dropdown panel.
 * Navbar (desktop) va Header (mobil) da ishlatiladi.
 * Alohida /notifications sahifasi o'rniga (konsolidatsiya).
 */
export function NotificationsBell({ className = 'text-[#8095AF] hover:text-white' }: NotificationsBellProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { notifications, isLoading, markAsRead, markAllAsRead, isMarkingAllAsRead } = useNotifications();

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // Tashqariga bosilganda yopish
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    if (open) {
      document.addEventListener('mousedown', handler);
      document.addEventListener('keydown', esc);
    }
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);

  const handleMarkOne = async (id: string, isRead: boolean) => {
    if (!isRead) await markAsRead(id);
  };

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`relative transition-all cursor-pointer min-h-[36px] min-w-[36px] p-1 flex items-center justify-center rounded-lg ${className}`}
        title="Bildirishnomalar"
        aria-label="Bildirishnomalar"
      >
        <Bell className="h-5 w-5 stroke-[2]" />
        {unreadCount > 0 && (
          <span className="absolute top-0.5 right-0.5 h-2 w-2 rounded-full bg-[#FF5C5C] animate-pulse" />
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="fixed inset-x-3 top-20 sm:absolute sm:inset-auto sm:right-0 sm:top-full sm:w-96 sm:mt-3 max-h-[70vh] overflow-hidden flex flex-col bg-[#2A3442] border-2 border-black rounded-3xl shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] z-50 animate-zoom-in font-ibm-plex-mono">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 px-4 py-3 border-b-2 border-black">
            <h3 className="text-sm font-black text-white flex items-center gap-2 font-montserrat uppercase tracking-wider">
              <Bell className="h-4 w-4 text-[#38C9E6]" /> Bildirishnomalar
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllAsRead()}
                disabled={isMarkingAllAsRead}
                className="text-[10px] uppercase font-extrabold text-[#38C9E6] hover:text-[#43E8A0] tracking-wider font-montserrat cursor-pointer disabled:opacity-50"
              >
                Barchasini o‘qish
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto flex flex-col divide-y-2 divide-black/40">
            {isLoading ? (
              <div className="p-6 text-center text-xs text-[#B0BEC5]">Yuklanmoqda...</div>
            ) : notifications.length === 0 ? (
              <div className="p-8 flex flex-col items-center gap-2 text-center">
                <Bell className="h-8 w-8 text-[#B0BEC5]" />
                <p className="text-xs text-[#B0BEC5]">Yangi bildirishnomalar yo‘q.</p>
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleMarkOne(notif.id, notif.is_read)}
                  className={`p-3.5 flex items-start gap-3 transition-all cursor-pointer group
                    ${!notif.is_read ? 'bg-[#2A3442] border-l-4 border-l-[#38C9E6]' : 'bg-[#2A3442]/60 opacity-75 hover:opacity-100'}`}
                >
                  <div className="h-8 w-8 rounded-lg bg-[#34495E] border-2 border-black flex items-center justify-center flex-shrink-0 mt-0.5 shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                    {getNotificationIcon(notif.type)}
                  </div>
                  <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                    <span className="text-xs font-extrabold text-white leading-tight font-montserrat truncate">
                      {notif.title || 'Platforma bildirishnomasi'}
                    </span>
                    <p className="text-[11px] text-[#B0BEC5] leading-snug line-clamp-2">
                      {notif.body || 'Yangi bildirishnoma mavjud.'}
                    </p>
                    <span className="text-[9px] text-[#B0BEC5] font-bold uppercase tracking-wider mt-1 flex items-center gap-1 font-montserrat">
                      <AlertCircle className="h-2.5 w-2.5 text-[#38C9E6]" /> {formatRelativeTime(notif.created_at)}
                    </span>
                  </div>
                  {!notif.is_read && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkOne(notif.id, notif.is_read);
                      }}
                      className="text-[#38C9E6] hover:text-[#43E8A0] p-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                      title="O‘qildi deb belgilash"
                      aria-label="O‘qildi deb belgilash"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
export default NotificationsBell;
