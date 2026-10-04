import { useTranslation } from 'react-i18next';
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSlots } from '@/features/slots/hooks';
import { useAuth } from '@/features/auth/hooks';
import { PageHeader, Button, Modal, EmptyState, Skeleton } from '@/shared/ui';
import { SlotCard, CreateSlotForm } from '@/features/slots/components';
import { SlotSearch } from '@/features/slots/components/SlotSearch';
import {
  Plus,
  SlidersHorizontal,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  List,
  Info,
  Search,
} from 'lucide-react';

type MainTab = 'my-slots' | 'search';

export default function SlotsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();

  // Main tab state
  const [mainTab, setMainTab] = useState<MainTab>('my-slots');

  // App layouts: 'calendar' (Scheduler grid) or 'list' (Card layout)
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [prefilledTime, setPrefilledTime] = useState<string>('');

  // Weekly calendar base date selector
  const [baseDate, setBaseDate] = useState<Date>(new Date());

  // Load slots and teachable items
  const {
    slots,
    isLoadingSlots,
    teachableProjects,
    createSlot,
    isCreatingSlot,
  } = useSlots();

  const handleCreateSubmit = async (data: any) => {
    await createSlot(data);
    setIsModalOpen(false);
    setPrefilledTime('');
  };

  const handleOpenNewSlot = () => {
    setPrefilledTime('');
    setIsModalOpen(true);
  };

  // Helper date functions for Week calendar
  const getMondayOfDate = (d: Date) => {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(date.setDate(diff));
    monday.setHours(0, 0, 0, 0);
    return monday;
  };

  const currentMonday = getMondayOfDate(baseDate);
  const weekDates = Array.from({ length: 7 }, (_, i) => {
    const nextDate = new Date(currentMonday);
    nextDate.setDate(currentMonday.getDate() + i);
    return nextDate;
  });

  const handlePrevWeek = () => {
    setBaseDate((prev) => {
      const next = new Date(prev);
      next.setDate(prev.getDate() - 7);
      return next;
    });
  };

  const handleNextWeek = () => {
    setBaseDate((prev) => {
      const next = new Date(prev);
      next.setDate(prev.getDate() + 7);
      return next;
    });
  };

  const handleToday = () => {
    setBaseDate(new Date());
  };

  const isSameDay = (d1: Date, d2: Date) => {
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    );
  };

  const slotsByDayHour = useMemo(() => {
    const map = new Map<string, typeof slots>();
    slots.forEach((slot) => {
      const slotDate = new Date(slot.start_time);
      const key = `${slotDate.getFullYear()}-${slotDate.getMonth()}-${slotDate.getDate()}-${slotDate.getHours()}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(slot);
    });
    return map;
  }, [slots]);

  const getSlotsForDayAndHour = (day: Date, hour: number) => {
    const key = `${day.getFullYear()}-${day.getMonth()}-${day.getDate()}-${hour}`;
    return slotsByDayHour.get(key) || [];
  };

  const handleCellClick = (dayDate: Date, hour: number) => {
    const selectedDate = new Date(dayDate);
    selectedDate.setHours(hour);
    selectedDate.setMinutes(0);
    selectedDate.setSeconds(0);

    const year = selectedDate.getFullYear();
    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDate.getDate()).padStart(2, '0');
    const hoursStr = String(selectedDate.getHours()).padStart(2, '0');
    const minutesStr = String(selectedDate.getMinutes()).padStart(2, '0');
    const formatted = `${year}-${month}-${day}T${hoursStr}:${minutesStr}`;

    setPrefilledTime(formatted);
    setIsModalOpen(true);
  };

  // Uzbek abbreviations
  const shortDaysUz = ['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'];
  const monthsUzLat = [
    'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
    'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr',
  ];

  const formatDayHeader = (date: Date) => {
    const dayName = shortDaysUz[date.getDay()];
    const dayNum = date.getDate();
    const monthName = monthsUzLat[date.getMonth()];
    return `${dayNum} ${monthName.slice(0, 3)}, ${dayName}`;
  };

  const formatWeekRange = (dates: Date[]) => {
    const first = dates[0];
    const last = dates[6];
    if (first.getMonth() === last.getMonth()) {
      return `${first.getDate()} - ${last.getDate()} ${monthsUzLat[first.getMonth()]}, ${first.getFullYear()}`;
    } else {
      return `${first.getDate()} ${monthsUzLat[first.getMonth()].slice(0, 3)} - ${last.getDate()} ${monthsUzLat[last.getMonth()].slice(0, 3)}, ${first.getFullYear()}`;
    }
  };

  const hours = Array.from({ length: 24 }, (_, i) => i);

  const filteredSlots = slots.filter((slot) => {
    if (statusFilter === 'all') return true;
    return slot.status === statusFilter;
  });

  const filterOptions = [
    { key: 'all', label: 'Barchasi' },
    { key: 'open', label: 'Ochiq' },
    { key: 'booked', label: 'Band' },
    { key: 'in_progress', label: 'Jarayonda' },
    { key: 'completed', label: 'Tugallandi' },
    { key: 'cancelled', label: 'Bekor' },
  ];

  const mainTabs = [
    { key: 'my-slots' as MainTab, label: 'Mening slotlarim', icon: CalendarClock },
    { key: 'search' as MainTab, label: 'Qidiruv', icon: Search },
  ];

  return (
    <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
      <PageHeader
        title="Baholash Slotlari"
        subtitle="Siz boshqaradigan o'qituvchi (reviewer) yoki o'quvchi (reviewee) dars jadvali."
        icon={CalendarClock}
        actions={
          mainTab === 'my-slots' ? (
            <Button
              variant="primary"
              onClick={handleOpenNewSlot}
              className="w-full sm:w-auto text-xs uppercase tracking-wider font-extrabold"
            >
              <Plus className="h-4 w-4" /> Yangi slot
            </Button>
          ) : undefined
        }
      />

      {/* Main tabs — neo-brutalist gradient active pattern */}
      <div className="flex gap-2 overflow-x-auto pb-3 border-b-2 border-black scrollbar-none">
        {mainTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = mainTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setMainTab(tab.key)}
              className={`flex items-center gap-2 px-4 h-11 min-h-[44px] rounded-xl text-xs font-bold uppercase tracking-wider font-montserrat border-2 select-none transition-all duration-150 whitespace-nowrap cursor-pointer
                ${
                  isActive
                    ? 'bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-black text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                    : 'bg-transparent border-transparent text-[#B0BEC5] hover:text-white hover:bg-gray-600/30'
                }
              `}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {mainTab === 'search' ? (
        <SlotSearch />
      ) : (
        <>
          {/* Mode selectors */}
          <div className="flex items-center justify-between border-b-2 border-black/30 pb-2">
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('calendar')}
                className={`px-3 sm:px-4 py-2 min-h-[44px] font-montserrat text-xs font-black uppercase tracking-widest border-b-4 transition-all duration-150 cursor-pointer flex items-center gap-1.5
                  ${
                    viewMode === 'calendar'
                      ? 'border-[#38C9E6] text-white'
                      : 'border-transparent text-[#B0BEC5] hover:text-white'
                  }
                `}
              >
                <CalendarDays className="h-4 w-4" />
                <span className="hidden sm:inline">Jadval</span>
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 sm:px-4 py-2 min-h-[44px] font-montserrat text-xs font-black uppercase tracking-widest border-b-4 transition-all duration-150 cursor-pointer flex items-center gap-1.5
                  ${
                    viewMode === 'list'
                      ? 'border-[#38C9E6] text-white'
                      : 'border-transparent text-[#B0BEC5] hover:text-white'
                  }
                `}
              >
                <List className="h-4 w-4" />
                <span className="hidden sm:inline">Ro'yxat</span>
              </button>
            </div>
          </div>

          {/* Mode content rendering */}
          {viewMode === 'calendar' ? (
            <div className="flex flex-col gap-4 animate-fade-in">
              {/* Calendar weekly controls bar */}
              <div className="flex flex-col gap-3 sm:gap-4 bg-[#1E2A38]/30 p-3 sm:p-4 rounded-2xl border-2 border-black">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={handlePrevWeek}
                    className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center bg-[#2A3442] hover:bg-gray-700 border-2 border-black rounded-xl text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer active:translate-y-[1px]"
                    aria-label="Avvalgi hafta"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={handleToday}
                    className="px-3 py-1.5 min-h-[44px] bg-[#2A3442] hover:bg-gray-700 border-2 border-black rounded-xl text-xs font-bold text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer"
                  >
                    Bugun
                  </button>
                  <button
                    onClick={handleNextWeek}
                    className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center bg-[#2A3442] hover:bg-gray-700 border-2 border-black rounded-xl text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer active:translate-y-[1px]"
                    aria-label="Keyingi hafta"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <span className="text-xs sm:text-sm font-extrabold text-white font-montserrat tracking-tight ml-1 sm:ml-2 truncate">
                    {formatWeekRange(weekDates)}
                  </span>
                </div>

                {/* Quick legend info keys */}
                <div className="flex flex-wrap items-center gap-3 text-[10px] font-bold text-[#B0BEC5]">
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#38C9E6] border border-black inline-block" />
                    <span>Ochiq</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#38C9E6] border border-black inline-block" />
                    <span>Band</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-black inline-block" />
                    <span>Jarayonda</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-zinc-600 border border-black inline-block" />
                    <span>Tugallangan</span>
                  </div>
                </div>
              </div>

              {/* Guidelines info */}
              <div className="flex items-start gap-2.5 bg-[#38C9E6]/5 border-2 border-[#38C9E6]/30 p-3 rounded-2xl text-xs text-[#38C9E6] leading-relaxed">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p>
                  <strong>Jadval ko'rsatmalari:</strong> Slot ochish uchun mos keladigan kun va soat katakchasini ustiga bosing. Mavjud ochilgan slotlarni o'zgartirish yoki tekshirish uchun slot ustiga bosing.
                </p>
              </div>

              {/* Real interactive scheduler week-grid */}
              <div className="w-full overflow-x-auto border-2 border-black rounded-3xl bg-[#2A3442] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                <div className="min-w-[700px] sm:min-w-[950px]">
                  {/* Header row containing days of selected week */}
                  <div className="grid grid-cols-8 border-b-2 border-black bg-[#1E2A38]/60 h-12 sm:h-14 items-center text-center">
                    <div className="border-r-2 border-black h-full flex items-center justify-center text-[9px] sm:text-[10px] text-[#B0BEC5] uppercase tracking-wider font-extrabold font-montserrat">
                      Vaqt
                    </div>
                    {weekDates.map((date, i) => {
                      const isTodayActive = isSameDay(date, new Date());
                      return (
                        <div
                          key={i}
                          className={`h-full flex flex-col justify-center border-r-2 border-black last:border-r-0 px-0.5 ${
                            isTodayActive ? 'bg-[#38C9E6]/10 text-[#38C9E6]' : 'text-white'
                          }`}
                        >
                          <span className="text-[9px] sm:text-[11px] font-extrabold font-montserrat tracking-tight leading-none">
                            {formatDayHeader(date)}
                          </span>
                          {isTodayActive && (
                            <span className="text-[7px] sm:text-[7.5px] font-black tracking-widest uppercase text-[#38C9E6] mt-1 font-ibm-plex-mono">
                              BUGUN
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Grid content containing 24 horizontal block rows */}
                  <div className="max-h-[450px] sm:max-h-[550px] overflow-y-auto divide-y-2 divide-black/30">
                    {hours.map((hour) => {
                      const hourStr = `${String(hour).padStart(2, '0')}:00`;
                      return (
                        <div
                          key={hour}
                          className="grid grid-cols-8 h-16 sm:h-20 hover:bg-white/[0.02] transition-colors"
                        >
                          {/* Left time label */}
                          <div className="border-r-2 border-black bg-[#1E2A38]/30 flex items-center justify-center font-mono font-bold text-[10px] sm:text-xs text-[#B0BEC5] select-none">
                            {hourStr}
                          </div>

                          {/* Day cells for week */}
                          {weekDates.map((dayDate, dayIdx) => {
                            const cellSlots = getSlotsForDayAndHour(dayDate, hour);
                            const isPastDate = new Date(dayDate);
                            isPastDate.setHours(hour);
                            const isPast = isPastDate.getTime() < Date.now();

                            return (
                              <div
                                key={dayIdx}
                                onClick={() => handleCellClick(dayDate, hour)}
                                className={`border-r-2 border-black/25 last:border-r-0 p-0.5 sm:p-1 flex flex-col gap-0.5 sm:gap-1 relative group cursor-pointer select-none transition-all duration-150 min-h-full justify-start
                                  ${isPast ? 'bg-black/10' : 'hover:bg-[#43E8A0]/10'}
                                `}
                              >
                                {/* Hover overlay plus button indicator */}
                                {cellSlots.length === 0 && (
                                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-all">
                                    <span className="p-1 rounded-lg bg-[#43E8A0] border border-black shadow-[1px_1px_0px_rgba(0,0,0,1)] text-black">
                                      <Plus className="h-3 w-3 sm:h-3.5 sm:w-3.5 stroke-[3]" />
                                    </span>
                                  </div>
                                )}

                                {/* Inside cell list cards */}
                                {cellSlots.map((slot) => {
                                  let statusClass = 'bg-[#38C9E6]/15 text-[#38C9E6] border-[#38C9E6]/40 hover:border-[#38C9E6]';
                                  if (slot.status === 'booked') {
                                    statusClass = 'bg-[#38C9E6]/15 text-[#38C9E6] border-[#38C9E6]/40 hover:border-[#38C9E6]';
                                  } else if (slot.status === 'in_progress') {
                                    statusClass = 'bg-amber-500/15 text-amber-400 border-amber-500/40 hover:border-amber-500';
                                  } else if (slot.status === 'completed') {
                                    statusClass = 'bg-zinc-700/40 text-[#B0BEC5] border-zinc-700 hover:border-zinc-500';
                                  } else if (slot.status === 'cancelled') {
                                    statusClass = 'bg-red-500/10 text-red-400 border-red-500/20 hover:border-red-500/50';
                                  }

                                  return (
                                    <div
                                      key={slot.id}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        navigate(`/slots/${slot.id}`);
                                      }}
                                      className={`px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-lg border-2 text-[8px] sm:text-[9px] font-bold truncate leading-tight transition-all shadow-[1.5px_1.5px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-0.5 justify-center ${statusClass}`}
                                      title={`${slot.reviewer_project} (${slot.status})`}
                                    >
                                      <div className="font-extrabold truncate text-white leading-none mb-0.5">
                                        {slot.reviewer_project}
                                      </div>
                                      <div className="flex items-center justify-between text-[7px] sm:text-[8px] opacity-80 leading-none">
                                        <span className="uppercase font-mono tracking-tighter">
                                          {slot.status === 'open' ? t('slots.statusOpen') : slot.status === 'booked' ? t('slots.statusBooked') : slot.status}
                                        </span>
                                        <span>{slot.is_online ? 'ON' : 'OFF'}</span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Card list layout fallback of slots */
            <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in">
              {/* Filters */}
              <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto pb-3 border-b-2 border-black scrollbar-none">
                <SlidersHorizontal className="h-4 w-4 text-[#38C9E6] flex-shrink-0" />
                <div className="flex gap-2">
                  {filterOptions.map((opt) => (
                    <button
                      key={opt.key}
                      onClick={() => setStatusFilter(opt.key)}
                      className={`px-3 py-1.5 min-h-[36px] rounded-xl text-xs font-bold uppercase tracking-wider font-montserrat select-none transition-all border-2 whitespace-nowrap cursor-pointer
                        ${
                          statusFilter === opt.key
                            ? 'bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-black text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                            : 'bg-[#2A3442] border-black text-[#B0BEC5] hover:text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px]'
                        }
                      `}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {isLoadingSlots ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div
                      key={i}
                      className="bg-[#2A3442] p-4 sm:p-6 rounded-3xl border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4 animate-pulse"
                    >
                      <div className="h-6 w-1/2 bg-gray-700 rounded" />
                      <div className="h-4 w-3/4 bg-gray-700 rounded mt-2" />
                      <div className="h-10 bg-gray-700 rounded mt-4" />
                    </div>
                  ))}
                </div>
              ) : filteredSlots.length === 0 ? (
                <EmptyState
                  title="Slotlar topilmadi"
                  description={"Ushbu filtr bo'yicha hech qanday dars yozuvi topilmadi. O'qitish uchun yangi dars ko'rsatkichi yaratishingiz mumkin."}
                  icon={<CalendarClock className="h-8 w-8 text-black" />}
                />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 animate-fade-in">
                  {filteredSlots.map((slot) => (
                    <SlotCard key={slot.id} slot={slot} currentUserId={user?.id} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Modal Wrapper for Creating slots */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setPrefilledTime('');
        }}
        title="Yangi Dars Slotini Yaratish"
      >
        <CreateSlotForm
          teachableProjects={teachableProjects}
          userCampus={user?.campus}
          onSubmit={handleCreateSubmit}
          isSubmitting={isCreatingSlot}
          initialStartTime={prefilledTime}
        />
      </Modal>
    </div>
  );
}
