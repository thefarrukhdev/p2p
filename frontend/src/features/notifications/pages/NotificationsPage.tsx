import { useNotifications } from '@/features/notifications/hooks';
import { Card, Badge, Spinner, Button, EmptyState, Skeleton } from '@/shared/ui';
import { formatRelativeTime } from '@/shared/lib/utils';
import { Bell, CheckSquare, Sparkles, BookOpen, AlertCircle } from 'lucide-react';

export default function NotificationsPage() {
  const { notifications, isLoading, markAsRead, markAllAsRead, isMarkingAllAsRead } = useNotifications();

  const handleMarkOne = async (id: string, isRead: boolean) => {
    if (!isRead) {
      await markAsRead(id);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'slot_booked':
        return <BookOpen className="h-5 w-5 text-[#38C9E6]" />;
      case 'slot_started':
        return <Sparkles className="h-5 w-5 text-[#ffd740]" />;
      case 'slot_completed':
        return <CheckSquare className="h-5 w-5 text-[#43E8A0]" />;
      default:
        return <Bell className="h-5 w-5 text-[#B0BEC5]" />;
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in font-ibm-plex-mono text-white">
      {/* Title block */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b-2 border-black pb-4">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2 font-montserrat tracking-tight leading-tight">
            <Bell className="h-6 w-6 text-[#38C9E6] shrink-0" /> Bildirishnomalar markazi
          </h1>
          <p className="text-xs text-[#B0BEC5] leading-relaxed">
            Slotlar darsi, boshlanishi yoki baholash fikrlari bo‘yicha real-vaqt yangiliklari.
          </p>
        </div>
        {notifications.some((n) => !n.is_read) && (
          <Button
            variant="secondary"
            onClick={() => markAllAsRead()}
            disabled={isMarkingAllAsRead}
            className="w-full sm:w-auto text-xs uppercase font-extrabold tracking-wider font-montserrat"
          >
            Barchasini o‘qilgan qilish
          </Button>
        )}
      </div>

      {/* Main logs display */}
      {isLoading ? (
        <div className="flex flex-col gap-4 animate-pulse-subtle">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-4 rounded-2xl border-2 border-black bg-[#2A3442]/60 flex items-start gap-4 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              <Skeleton variant="rect" className="h-10 w-10 rounded-xl" />
              <div className="flex flex-col gap-2 w-full max-w-2xl">
                <Skeleton variant="text" className="w-1/3 h-4" />
                <Skeleton variant="text" className="w-[85%] h-3" />
                <Skeleton variant="text" className="w-16 h-2.5 mt-1" />
              </div>
            </div>
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <EmptyState
          title="Yangi bildirishnomalar yo'q"
          description="Bildirishnomalar qutisi bo‘sh. Tizimdagi dars yangiliklari shu yerda kelib turadi."
          icon={<Bell className="h-8 w-8 text-black" />}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              onClick={() => handleMarkOne(notif.id, notif.is_read)}
              className={`p-3 sm:p-4 rounded-2xl border-2 flex items-start justify-between gap-3 sm:gap-4 transition-all relative group cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]
                ${
                  !notif.is_read
                    ? 'bg-[#2A3442] border-black border-l-8 border-l-[#38C9E6]'
                    : 'bg-[#2A3442]/60 border-black opacity-75 hover:opacity-100'
                }
              `}
            >
              <div className="flex gap-3 sm:gap-4 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-xl bg-[#34495E] border-2 border-black flex items-center justify-center flex-shrink-0 mt-0.5 shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                  {getNotificationIcon(notif.type)}
                </div>

                <div className="flex flex-col gap-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-extrabold text-white leading-tight font-montserrat tracking-tight break-words">
                      {notif.title || 'Platforma bildirishnomasi'}
                    </span>
                    {!notif.is_read && (
                      <span className="h-2.5 w-2.5 rounded-full bg-[#FF9B9B] animate-pulse shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-[#B0BEC5] leading-relaxed max-w-2xl break-words">
                    {notif.body || 'Yangi bildirishnoma mavjud.'}
                  </p>
                  <span className="text-[9px] text-[#B0BEC5] font-black uppercase tracking-wider mt-1.5 flex items-center gap-1.5 font-montserrat">
                    <AlertCircle className="h-3 w-3 text-[#38C9E6] shrink-0" /> {formatRelativeTime(notif.created_at)}
                  </span>
                </div>
              </div>

              {/* Mark read toggle action inside list row */}
              {!notif.is_read && (
                <button
                  type="button"
                  className="text-[10px] uppercase font-extrabold text-[#38C9E6] hover:text-[#43E8A0] whitespace-nowrap hidden sm:block font-montserrat tracking-wider cursor-pointer"
                >
                  O‘qildi deb kiritish
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

