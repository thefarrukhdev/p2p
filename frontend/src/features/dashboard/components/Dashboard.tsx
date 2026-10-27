import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { useSlots } from '@/features/slots/hooks';
import { useAuth } from '@/features/auth/hooks';
import { useDashboard } from '@/features/dashboard/hooks';
import { useNotifications } from '@/features/notifications/hooks';
import { Slot, Notification } from '@/shared/types/api';
import { formatDateTime, formatRelativeTime } from '@/shared/lib/utils';
import { Button, Card, Badge, PageHeader, Skeleton, EmptyState } from '@/shared/ui';
import {
  Clock,
  ArrowRight,
  User,
  Bell,
  CalendarDays,
  LayoutDashboard,
  AlertTriangle,
  RefreshCw,
  Shield,
  Zap,
  Trophy,
  MapPin,
  Plus,
} from 'lucide-react';

export function Dashboard() {
  const { t } = useTranslation();
  const { user: authUser } = useAuth();
  const navigate = useNavigate();

  // P2P Corpus API Hooks
  const { dashboard, isLoading: isLoadingDashboard, isError: isErrorDashboard, refetch: refetchDashboard } = useDashboard();
  const { slots, isLoadingSlots, isErrorSlots, refetchSlots } = useSlots();
  const { notifications, markAsRead } = useNotifications();

  const currentUser = dashboard?.user || authUser;
  const levelProgress = dashboard?.xp_to_next_level ?? 65;

  // Filter up to 3 upcoming slots related to the current user (my schedule)
  const mySchedule = useMemo(() => {
    if (!slots || !currentUser?.id) return [];
    return slots
      .filter((slot: Slot) => {
        const isMySlot = slot.reviewer_id === currentUser.id || slot.reviewee_id === currentUser.id;
        return isMySlot && (slot.status === 'open' || slot.status === 'booked' || slot.status === 'in_progress');
      })
      .slice(0, 3);
  }, [slots, currentUser?.id]);

  // Filter 3 of the latest available open slots for discovery
  const availableSlots = useMemo(() => {
    if (!slots) return [];
    return slots
      .filter((slot: Slot) => slot.status === 'open' && slot.reviewer_id !== currentUser?.id)
      .slice(0, 3);
  }, [slots, currentUser?.id]);

  // Error state
  if (isErrorDashboard || isErrorSlots) {
    return (
      <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
        <PageHeader
          title={t('dashboard.title')}
          subtitle={t('dashboard.subtitle')}
          icon={LayoutDashboard}
        />
        <Card className="flex flex-col items-center justify-center py-12 gap-4 text-center">
          <AlertTriangle className="h-10 w-10 text-[#FF9B9B]" />
          <h3 className="text-sm font-extrabold text-[#FF9B9B] font-montserrat uppercase">
            {t('dashboard.errors.loadTitle')}
          </h3>
          <p className="text-xs text-[#B0BEC5]">
            {t('dashboard.errors.loadDesc')}
          </p>
          <Button
            variant="primary"
            onClick={() => {
              refetchDashboard();
              refetchSlots();
            }}
          >
            <RefreshCw className="h-4 w-4" /> {t('dashboard.reload')}
          </Button>
        </Card>
      </div>
    );
  }

  // Loading state
  if (isLoadingDashboard) {
    return (
      <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
        <PageHeader
          title={t('dashboard.title')}
          subtitle={t('dashboard.subtitle')}
          icon={LayoutDashboard}
        />
        {/* Profile skeleton */}
        <div className="flex items-center gap-4 pb-6 border-b-2 border-black/30">
          <Skeleton variant="circle" className="h-14 w-14 sm:h-16 sm:w-16" />
          <div className="flex flex-col gap-2">
            <Skeleton variant="text" className="w-32 sm:w-40 h-5" />
            <Skeleton variant="text" className="w-20 sm:w-24 h-3" />
          </div>
        </div>
        {/* Stats skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-4">
          {[1, 2, 3, 4].map((n) => (
            <Skeleton key={n} variant="rect" className="h-16 sm:h-20 rounded-2xl" />
          ))}
        </div>
        {/* Content skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          <div className="flex flex-col gap-3">
            <Skeleton variant="text" className="w-32 h-4" />
            {[1, 2, 3].map((n) => (
              <Skeleton key={n} variant="rect" className="h-24 rounded-2xl" />
            ))}
          </div>
          <div className="flex flex-col gap-3">
            <Skeleton variant="text" className="w-32 h-4" />
            {[1, 2, 3].map((n) => (
              <Skeleton key={n} variant="rect" className="h-20 rounded-2xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        icon={LayoutDashboard}
      />

      {/* ── PROFILE HEADER SECTION ── */}
      <header className="flex flex-col gap-4 sm:gap-6 pb-4 sm:pb-6 border-b-2 border-black/30">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="relative flex-shrink-0">
              <div className="h-14 w-14 sm:h-16 sm:w-16 rounded-full border-2 border-black bg-[#1E2A38] overflow-hidden flex items-center justify-center shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                {currentUser?.avatar_url ? (
                  <img
                    src={currentUser.avatar_url}
                    alt={currentUser.login || currentUser.school21_login}
                    className="h-full w-full object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <User className="h-5 w-5 sm:h-6 sm:w-6 text-[#38C9E6]" />
                )}
              </div>
              <span className="absolute -bottom-1 -right-1 bg-[#43E8A0] text-black text-[9px] font-black px-1.5 py-0.5 rounded-full border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                Lvl {currentUser?.level ?? 1}
              </span>
            </div>

            <div className="min-w-0">
              <h2 className="text-lg sm:text-xl font-black text-white font-montserrat tracking-tight leading-none truncate">
                {currentUser?.first_name || currentUser?.login || currentUser?.school21_login || t('dashboard.profile.student')}
              </h2>
              <p className="text-xs text-[#B0BEC5] flex items-center gap-1.5 mt-1.5 leading-none flex-wrap">
                <span className="truncate">{currentUser?.core_program || t('dashboard.profile.coreProgram')}</span>
                <span>·</span>
                <span className="text-[#43E8A0] font-bold truncate">{currentUser?.main_track || 'Yo\'nalish'}</span>
              </p>
            </div>
          </div>

          {/* Level XP Progress Bar */}
          <div className="w-full sm:w-[240px] flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-[10px] font-bold">
              <span className="text-[#B0BEC5]">{t('dashboard.profile.levelProgress')}</span>
              <span className="text-[#43E8A0] font-black">{levelProgress}%</span>
            </div>
            <div className="w-full h-2 rounded-lg bg-[#34495E] border-2 border-black overflow-hidden shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
              <div
                className="h-full rounded-lg bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] transition-all duration-300"
                style={{ width: `${levelProgress}%` }}
              />
            </div>
          </div>
        </div>
      </header>

      {/* ── KEY PERFORMANCE STATS ROW ── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-4">
        {[
          { label: t('dashboard.stats.coalition'), value: currentUser?.coalition_name || t('dashboard.stats.noCoalition'), icon: Shield, color: 'text-[#38C9E6]' },
          { label: t('dashboard.stats.peerPoints'), value: `${currentUser?.peer_points ?? 0} PRP`, icon: Zap, color: 'text-[#ffd740]' },
          { label: t('dashboard.stats.experience'), value: `${currentUser?.xp ?? 0} XP`, icon: Trophy, color: 'text-[#43E8A0]' },
          { label: t('dashboard.stats.location'), value: currentUser?.current_location || t('dashboard.stats.offline'), icon: MapPin, color: 'text-[#B0BEC5]' },
        ].map((stat, idx) => (
          <div
            key={idx}
            className="bg-[#2A3442] border-2 border-black rounded-2xl p-3 sm:p-4 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] sm:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col text-left justify-between hover:translate-x-[1px] hover:translate-y-[1px] transition-all min-w-0"
          >
            <div className="flex items-center justify-between gap-1">
              <span className="text-[9px] sm:text-[10px] text-[#B0BEC5] uppercase tracking-wider font-extrabold truncate">{stat.label}</span>
              <stat.icon className={`h-3.5 w-3.5 ${stat.color} shrink-0`} />
            </div>
            <span className="text-xs sm:text-sm font-black text-white font-montserrat truncate mt-1.5">
              {stat.value}
            </span>
          </div>
        ))}
      </section>

      {/* ── CENTRAL AGENDA & ACTIVITY LAYOUT ── */}
      <main className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">

        {/* PANEL A: UPCOMING SCHEDULE */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b-2 border-black/20 pb-2">
            <h2 className="text-xs font-black text-[#B0BEC5] uppercase tracking-wider font-montserrat flex items-center gap-1.5">
              <CalendarDays className="h-4 w-4 text-[#38C9E6]" />
              {t('dashboard.schedule.title')}
            </h2>
            <Link
              to="/slots"
              className="min-h-[44px] inline-flex items-center py-2 px-1 text-[10px] font-black text-[#38C9E6] hover:text-[#43E8A0] transition-colors uppercase font-montserrat"
            >
              {t('dashboard.schedule.viewAll')}
            </Link>
          </div>

          <div className="flex flex-col gap-3">
            {isLoadingSlots ? (
              <div className="flex flex-col gap-3">
                {[1, 2, 3].map((n) => (
                  <Skeleton key={n} variant="rect" className="h-24 rounded-2xl" />
                ))}
              </div>
            ) : mySchedule.length === 0 ? (
              <div className="py-7 px-4 rounded-2xl border-2 border-black bg-[#2A3442] flex flex-col items-center justify-center text-center gap-3 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                <div className="h-10 w-10 rounded-xl bg-[#34495E] border-2 border-black flex items-center justify-center text-[#38C9E6] shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                  <CalendarDays className="h-5 w-5" />
                </div>
                <p className="text-xs text-[#B0BEC5]">{t('dashboard.schedule.empty')}</p>
                <Button
                  variant="primary"
                  onClick={() => navigate('/slots')}
                  className="text-xs uppercase tracking-wider font-extrabold"
                >
                  <Plus className="h-4 w-4" /> {t('dashboard.schedule.addSlot')}
                </Button>
              </div>
            ) : (
              mySchedule.map((slot) => {
                const isReviewer = slot.reviewer_id === currentUser?.id;
                const statusType = slot.status === 'open' ? 'success' : slot.status === 'booked' ? 'primary' : 'warning';

                return (
                  <Card
                    key={slot.id}
                    onClick={() => navigate(`/slots/${slot.id}`)}
                    className="flex flex-col gap-2"
                  >
                    <div className="flex items-start justify-between gap-2 sm:gap-4">
                      <div className="flex flex-col min-w-0 flex-1">
                        <span className="text-[8px] font-black text-[#B0BEC5] tracking-widest uppercase">
                          {isReviewer ? t('dashboard.schedule.reviewer') : t('dashboard.schedule.reviewee')}
                        </span>
                        <h3 className="text-sm font-black text-white font-montserrat truncate mt-1">
                          {slot.reviewer_project}
                        </h3>
                      </div>
                      <Badge type={statusType}>
                        {slot.status === 'open' ? t('dashboard.schedule.statusOpen') : slot.status === 'booked' ? t('dashboard.schedule.statusBooked') : t('dashboard.schedule.statusActive')}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 sm:gap-3 text-[10px] text-[#B0BEC5] font-bold border-t-2 border-black/10 pt-2 mt-1 flex-wrap">
                      <Clock className="h-3.5 w-3.5 text-[#38C9E6] flex-shrink-0" />
                      <span className="truncate min-w-0">{formatDateTime(slot.start_time)}</span>
                      <span>·</span>
                      <span className="uppercase text-white">{slot.campus}</span>
                    </div>
                  </Card>
                );
              })
            )}
          </div>
        </section>

        {/* PANEL B: RECENT NOTIFICATIONS */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b-2 border-black/20 pb-2">
            <h2 className="text-xs font-black text-[#B0BEC5] uppercase tracking-wider font-montserrat flex items-center gap-1.5">
              <Bell className="h-4 w-4 text-[#38C9E6]" />
              {t('dashboard.notifications.title')}
            </h2>
          </div>

          <div className="flex flex-col gap-3">
            {notifications.slice(0, 3).length === 0 ? (
              <div className="py-7 px-4 rounded-2xl border-2 border-black bg-[#2A3442] flex flex-col items-center justify-center text-center gap-2.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                <div className="h-10 w-10 rounded-xl bg-[#34495E] border-2 border-black flex items-center justify-center text-[#B0BEC5] shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                  <Bell className="h-5 w-5" />
                </div>
                <p className="text-xs text-[#B0BEC5]">{t('dashboard.notifications.empty')}</p>
              </div>
            ) : (
              notifications.slice(0, 3).map((notif: Notification) => (
                <Card
                  key={notif.id}
                  onClick={() => {
                    if (!notif.is_read) {
                      try { markAsRead(notif.id); } catch { /* silent */ }
                    }
                    if (notif.slot_id) {
                      navigate(`/slots/${notif.slot_id}`);
                    }
                  }}
                  className={`flex flex-col text-left relative ${!notif.is_read ? 'border-l-4 border-l-[#43E8A0]' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-[#B0BEC5] font-black">
                      {formatRelativeTime(notif.created_at)}
                    </span>
                    {!notif.is_read && (
                      <span className="h-2 w-2 rounded-full bg-[#43E8A0]" />
                    )}
                  </div>
                  <h4 className="text-xs font-extrabold text-white mt-1.5 font-montserrat">
                    {notif.title || t('dashboard.notifications.defaultTitle')}
                  </h4>
                  <p className="text-[11px] text-[#B0BEC5] mt-1 line-clamp-1">
                    {notif.body}
                  </p>
                </Card>
              ))
            )}
          </div>
        </section>

      </main>

      {/* ── AVAILABLE SLOTS DISCOVERY GRID ── */}
      <section className="border-t-2 border-black/20 pt-6 sm:pt-8 flex flex-col gap-4 sm:gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex flex-col">
            <h2 className="text-xs font-black text-[#B0BEC5] uppercase tracking-wider font-montserrat">
              {t('dashboard.available.title')}
            </h2>
            <p className="text-[11px] text-[#B0BEC5] mt-0.5">{t('dashboard.available.desc')}</p>
          </div>
          <Link
            to="/slots"
            className="min-h-[44px] inline-flex items-center py-2 px-1 text-[10px] font-black text-[#38C9E6] hover:text-[#43E8A0] transition-colors uppercase font-montserrat"
          >
            {t('dashboard.available.viewAll')}
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
          {isLoadingSlots ? (
            [1, 2, 3].map((n) => (
              <Skeleton key={n} variant="rect" className="h-24 rounded-2xl" />
            ))
          ) : availableSlots.length === 0 ? (
            <div className="col-span-1 sm:col-span-2 md:col-span-3 py-7 px-4 text-center border-2 border-black rounded-2xl bg-[#2A3442] shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex flex-col items-center justify-center gap-2">
              <p className="text-xs text-[#B0BEC5]">{t('dashboard.available.empty')}</p>
            </div>
          ) : (
            availableSlots.map((slot) => (
              <Card
                key={slot.id}
                onClick={() => navigate(`/slots/${slot.id}`)}
                className="flex flex-col gap-2 justify-between"
              >
                <div className="flex flex-col">
                  <span className="text-[8px] font-black text-[#B0BEC5] uppercase tracking-widest leading-none">{t('dashboard.available.availableSlot')}</span>
                  <h4 className="text-xs font-black text-white mt-1.5 font-montserrat truncate">
                    {slot.reviewer_project}
                  </h4>
                </div>

                <div className="flex flex-col gap-0.5 text-[10px] text-[#B0BEC5] border-t-2 border-black/10 pt-2 mt-2 font-bold">
                  <span className="truncate text-[#38C9E6]">{formatDateTime(slot.start_time)}</span>
                  <span className="uppercase text-white text-[9px]">{slot.campus}</span>
                </div>
              </Card>
            ))
          )}
        </div>
      </section>

      {/* ── QUICK ACTION FOOTER ── */}
      <footer className="border-t-2 border-black/30 pt-4 sm:pt-6 mt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-xs text-[#B0BEC5] text-center sm:text-left">
          {t('dashboard.footer.desc')}
        </p>
        <Button
          variant="primary"
          onClick={() => navigate('/slots')}
          className="w-full sm:w-auto"
        >
          {t('dashboard.footer.btn')} <ArrowRight className="h-4 w-4" />
        </Button>
      </footer>
    </div>
  );
}

export default Dashboard;
