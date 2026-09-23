import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { slotsService } from '@/features/slots/api';
import { useAuth } from '@/features/auth/hooks';
import { formatDateTime } from '@/shared/lib/utils';
import { useSlots } from '@/features/slots/hooks';
import {
  Card,
  Badge,
  Button,
  Skeleton,
  Modal,
} from '@/shared/ui';
import { SlotTimeline } from '@/features/slots/components';
import { ReviewModal } from '@/features/reviews/components/ReviewModal';
import {
  Calendar,
  Laptop,
  MapPin,
  Clock,
  User,
  Play,
  CheckCircle,
  ChevronLeft,
} from 'lucide-react';
import { useEffect, useState } from 'react';

// Live helper function to calculate minutes passed
const getMinutesPassed = (startTimeStr?: string | null) => {
  if (!startTimeStr) return 0;
  const start = new Date(startTimeStr).getTime();
  const now = Date.now();
  return Math.floor((now - start) / 1000 / 60);
};

export default function SlotDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [showAbsentModal, setShowAbsentModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);

  // Load slot querying from separate server query cache
  const { data: slot, isLoading, isError, refetch } = useQuery({
    queryKey: ['slot', id],
    queryFn: () => slotsService.getSlotById(id || ''),
    enabled: !!id,
    refetchInterval: 10000, // Sync status automatically every 10s
  });

  const {
    startSlot,
    finishSlot,
    cancelSlot,
    absentSlot,
    isStartingSlot,
    isFinishingSlot,
    isCancellingSlot,
    isAbsentingSlot,
  } = useSlots();

  // Tracker state for 15 minutes elapsed rule
  const [minutesPassed, setMinutesPassed] = useState(0);

  useEffect(() => {
    if (slot && slot.actual_start) {
      setMinutesPassed(getMinutesPassed(slot.actual_start));
      const interval = setInterval(() => {
        setMinutesPassed(getMinutesPassed(slot.actual_start));
      }, 30000); // refresh every 30s
      return () => clearInterval(interval);
    }
  }, [slot]);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white animate-pulse-subtle">
        {/* Top Breadcrumb Nav */}
        <div>
          <Skeleton variant="text" className="w-32 h-3" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Left Side: Main Details panel */}
          <div className="lg:col-span-2 flex flex-col gap-4 sm:gap-6">
            <div className="p-4 sm:p-6 flex flex-col gap-5 bg-[#2A3442] border-2 border-black rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 border-b-2 border-black pb-4">
                <div className="flex flex-col gap-2 w-full sm:w-2/3">
                  <Skeleton variant="text" className="w-1/3 h-3" />
                  <Skeleton variant="text" className="w-[85%] h-5" />
                </div>
                <Skeleton variant="rect" className="w-16 h-6 rounded-md" />
              </div>

              {/* Core Specs Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 py-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-2xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                    <Skeleton variant="circle" className="h-5 w-5" />
                    <div className="flex flex-col gap-2 w-full">
                      <Skeleton variant="text" className="w-1/3 h-2.5" />
                      <Skeleton variant="text" className="w-2/3 h-3" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Side: Timeline steps overview */}
          <div className="lg:col-span-1">
            <div className="p-4 sm:p-6 bg-[#2A3442] border-2 border-black rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4">
              <Skeleton variant="text" className="w-1/2 h-4 border-b-2 border-black/20 pb-2" />
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex gap-3">
                  <Skeleton variant="circle" className="h-4 w-4 mt-0.5" />
                  <div className="flex flex-col gap-1 w-full">
                    <Skeleton variant="text" className="w-1/2 h-3" />
                    <Skeleton variant="text" className="w-1/3 h-2.5" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !slot) {
    return (
      <div className="py-12 text-center font-ibm-plex-mono text-white">
        <p className="text-[#FF9B9B] font-extrabold">Tafsilotlarni yuklashda xatolik yuz berdi.</p>
        <Link to="/slots" className="text-xs uppercase tracking-wider text-[#38C9E6] underline font-montserrat">
          Slotlar ro'yxatiga qaytish
        </Link>
      </div>
    );
  }

  const isReviewer = slot.reviewer_id === user?.id;
  const isReviewee = slot.reviewee_id === user?.id;

  const getStatusBadge = () => {
    switch (slot.status) {
      case 'open':
        return <Badge type="success">Ochiq</Badge>;
      case 'booked':
        return <Badge type="info">Band qilingan</Badge>;
      case 'in_progress':
        return <Badge type="warning">Jarayonda</Badge>;
      case 'completed':
        return <Badge type="primary">Tugallandi</Badge>;
      case 'cancelled':
        return <Badge type="error">Bekor qilingan</Badge>;
      case 'absent':
        return <Badge type="error">Kelmadi</Badge>;
      default:
        return <Badge type="info">{slot.status}</Badge>;
    }
  };

  // Stage flags
  const canCancel = (isReviewer && slot.status !== 'completed' && slot.status !== 'cancelled' && slot.status !== 'absent');
  
  // Can start only if status is booked and we are within 15 minutes of the start time (or past it)
  const isTimeValidToStart = new Date().getTime() >= new Date(slot.start_time).getTime() - 15 * 60 * 1000;
  
  const hasStarted = isReviewer ? slot.reviewer_started : slot.reviewee_started;
  const partnerStarted = isReviewer ? slot.reviewee_started : slot.reviewer_started;
  
  const canStart = slot.status === 'booked' && (isReviewer || isReviewee) && isTimeValidToStart && !hasStarted;
  const canFinish = slot.status === 'in_progress' && (isReviewer || isReviewee);

  // Minutes criteria for finishing evaluation: 15 minutes
  const readyToFinish = minutesPassed >= 15;

  // Actions
  const handleStart = async () => {
    try {
      await startSlot(slot.id);
      refetch();
    } catch (_e) { /* handled */ }
  };

  const handleFinish = async () => {
    try {
      await finishSlot(slot.id);
      refetch();
    } catch (_e) { /* handled */ }
  };

  const handleCancel = () => {
    setCancelReason('');
    setShowCancelModal(true);
  };

  const handleConfirmCancel = async () => {
    setShowCancelModal(false);
    try {
      await cancelSlot({ id: slot.id, reason: cancelReason || undefined });
      refetch();
    } catch (_e) { /* handled */ }
  };

  const handleAbsent = () => {
    setShowAbsentModal(true);
  };

  const handleConfirmAbsent = async () => {
    setShowAbsentModal(false);
    try {
      await absentSlot(slot.id);
      refetch();
    } catch (_e) { /* handled */ }
  };

  return (
    <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
      {/* Top Breadcrumb Nav */}
      <div>
        <Link
          to="/slots"
          className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-[#B0BEC5] hover:text-white transition-colors font-montserrat min-h-[44px]"
        >
          <ChevronLeft className="h-4 w-4 text-[#38C9E6]" /> Slotlar ro'yxati
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left Side: Main Details panel */}
        <div className="lg:col-span-2 flex flex-col gap-4 sm:gap-6">
          <Card hover={false} className="p-4 sm:p-6 flex flex-col gap-4 sm:gap-5 bg-[#2A3442] border-2 border-black rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] relative z-10">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 sm:gap-0 border-b-2 border-black pb-4">
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-[#38C9E6] font-black tracking-widest uppercase font-montserrat">
                  DARS MATNI & DETALLARI
                </span>
                <h2 className="text-lg sm:text-xl font-black text-white font-montserrat tracking-tight leading-none truncate max-w-[280px] sm:max-w-none">
                  {slot.reviewer_project}
                </h2>
              </div>
              <div className="self-start">{getStatusBadge()}</div>
            </div>

            {/* Core Specs Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-sm py-2">
              <div className="flex items-center gap-3 p-3 rounded-2xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <Calendar className="h-5 w-5 text-[#38C9E6] flex-shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-[10px] text-[#B0BEC5] font-extrabold uppercase font-montserrat">Haqiqiy Vaqt</span>
                  <span className="text-xs font-bold truncate">{formatDateTime(slot.start_time)}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-2xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <Laptop className="h-5 w-5 text-[#cdbdff] flex-shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-[10px] text-[#B0BEC5] font-extrabold uppercase font-montserrat">Formati</span>
                  <span className="text-xs font-bold truncate">{slot.is_online ? 'Onlayn (Masofaviy)' : 'Oflayn (Campus)'}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-2xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <MapPin className="h-5 w-5 text-[#ffd740] flex-shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-[10px] text-[#B0BEC5] font-extrabold uppercase font-montserrat">Kampus joylashuvi</span>
                  <span className="text-xs font-bold uppercase">{slot.campus}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-2xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <User className="h-5 w-5 text-[#38C9E6] flex-shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-[10px] text-[#B0BEC5] font-extrabold uppercase font-montserrat">Roli</span>
                  <span className="text-xs font-bold">
                    {isReviewer ? "O'qituvchi (Siz)" : isReviewee ? "O'quvchi (Siz)" : 'Talaba'}
                  </span>
                </div>
              </div>
            </div>

            {/* Extra student project detail */}
            {slot.reviewee_project && (
              <div className="p-3 sm:p-4 bg-[#34495E] rounded-2xl border-2 border-black text-xs text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <span className="font-extrabold text-[#B0BEC5] font-montserrat uppercase tracking-wider">Tekshirilayotgan loyiha:</span>
                <strong className="text-[#43E8A0] uppercase font-montserrat font-black truncate">{slot.reviewee_project}</strong>
              </div>
            )}

            {/* In Progress Time Lock Warning */}
            {slot.status === 'in_progress' && (
              <div className="p-3 sm:p-4 rounded-2xl bg-[#4A3D2D] border-2 border-black text-xs text-white leading-relaxed flex items-start gap-3 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] mt-2">
                <Clock className="h-5 w-5 text-[#ffd740] flex-shrink-0 mt-0.5 animate-pulse" />
                <div className="flex flex-col gap-0.5">
                  <span className="font-black uppercase tracking-widest text-[10px] text-[#ffd740] font-montserrat">Ma'lumot muddatlari</span>
                  <span className="font-medium leading-relaxed">
                    Dars boshlanganidan buyon {minutesPassed} daqiqa o'tdi. Darsni yakunlash uchun kamida 15 daqiqa
                    o'tishi shart ({15 - Math.min(15, minutesPassed)} daqiqa kutilmoqda).
                  </span>
                </div>
              </div>
            )}

            {/* Context Active Action Triggers */}
            <div className="flex flex-col sm:flex-row flex-wrap gap-3 pt-4 border-t-2 border-black/30 sm:justify-end mt-2">
              {/* Trigger evaluation cancel (Only reviewer) */}
              {canCancel && (
                <Button variant="danger" onClick={handleCancel} disabled={isCancellingSlot} className="w-full sm:w-auto font-montserrat uppercase font-extrabold tracking-wider text-xs">
                  Slotni bekor qilish
                </Button>
              )}

              {/* Trigger Absence complaint */}
              {(slot.status === 'booked' || slot.status === 'in_progress') && (isReviewer || isReviewee) && (
                <Button variant="ghost" onClick={handleAbsent} disabled={isAbsentingSlot} className="w-full sm:w-auto text-[#FF9B9B] hover:bg-[#FF9B9B]/5 border-2 border-transparent hover:border-black font-montserrat uppercase font-extrabold tracking-wider text-xs">
                  Sherik kelmadi
                </Button>
              )}

              {/* Trigger start slot */}
              {canStart && (
                <Button variant="primary" onClick={handleStart} disabled={isStartingSlot} className="w-full sm:w-auto font-montserrat uppercase font-extrabold tracking-wider text-xs text-black">
                  <Play className="h-4 w-4 fill-current" /> Darsni boshlash
                </Button>
              )}

              {/* Waiting for partner */}
              {slot.status === 'booked' && hasStarted && (
                <Button variant="primary" disabled className="w-full sm:w-auto font-montserrat uppercase font-extrabold tracking-wider text-xs text-black opacity-70">
                  <Clock className="h-4 w-4 fill-current mr-2 animate-pulse" /> Sherik kutilmoqda...
                </Button>
              )}

              {/* Trigger complete slot */}
              {canFinish && (
                <Button
                  variant="primary"
                  onClick={handleFinish}
                  disabled={isFinishingSlot || !readyToFinish}
                  title={!readyToFinish ? "Darsni yakunlash uchun 15 daqiqa o'tishi shart" : ''}
                  className="w-full sm:w-auto font-montserrat uppercase font-extrabold tracking-wider text-xs text-black"
                >
                  <CheckCircle className="h-4 w-4" /> Darsni yakunlash
                </Button>
              )}

              {slot.status === 'completed' && (
                <Button
                  variant="primary"
                  onClick={() => setShowReviewModal(true)}
                  className="w-full sm:w-auto font-montserrat uppercase font-extrabold tracking-wider text-xs text-black"
                >
                  Fikr-Mulohaza qoldirish
                </Button>
              )}
            </div>
          </Card>
        </div>

        {/* Right Side: Timeline steps overview */}
        <div className="lg:col-span-1">
          <SlotTimeline
            status={slot.status}
            actualStart={slot.actual_start}
            actualEnd={slot.actual_end}
          />
        </div>
      </div>

      {showCancelModal && (
        <Modal
          isOpen={showCancelModal}
          onClose={() => setShowCancelModal(false)}
          title="Slotni Bekor Qilish"
        >
          <div className="flex flex-col gap-4">
            <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed">
              Ushbu slotni bekor qilmoqchimisiz? Sababini quyida ko'rsatishingiz mumkin (ixtiyoriy):
            </p>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase font-bold text-[#B0BEC5] tracking-wider font-montserrat">SABAB (IXTIYORIY)</label>
              <input
                type="text"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Masalan: Shoshilinch ishim chiqib qoldi..."
                className="w-full h-11 min-h-[44px] px-4 py-2 border-2 border-black rounded-xl bg-[#34495E] text-white font-ibm-plex-mono focus:outline-none focus:ring-2 focus:ring-[#38C9E6] transition-all text-xs"
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowCancelModal(false)}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-[#34495E] hover:bg-gray-600 text-white font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                Orqaga
              </button>
              <button
                type="button"
                onClick={handleConfirmCancel}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-[#ff5252] text-white hover:bg-red-600 font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                Tasdiqlash
              </button>
            </div>
          </div>
        </Modal>
      )}

      {showAbsentModal && (
        <Modal
          isOpen={showAbsentModal}
          onClose={() => setShowAbsentModal(false)}
          title="Sherik Kelmadi deb Belgilash"
        >
          <div className="flex flex-col gap-4">
            <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed">
              Sherigingiz kutilayotgan dars vaqtiga haqiqatdan ham kelmadimi? Buni kelmadi deb belgilamoqchimisiz? Ushbu amal ortga qaytarilmaydi.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowAbsentModal(false)}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-[#34495E] hover:bg-gray-600 text-white font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                Yo'q, kuting
              </button>
              <button
                type="button"
                onClick={handleConfirmAbsent}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-[#ff5252] text-white hover:bg-red-600 font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                Ha, kelmadi
              </button>
            </div>
          </div>
        </Modal>
      )}

      {slot && (
        <ReviewModal
          slotId={slot.id}
          isOpen={showReviewModal}
          onClose={() => setShowReviewModal(false)}
        />
      )}
    </div>
  );
}
