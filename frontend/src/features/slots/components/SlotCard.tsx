import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Slot } from '@/shared/types/api';
import { Card, Badge } from '@/shared/ui';
import { formatDateTime } from '@/shared/lib/utils';
import { Calendar, Laptop, MapPin, ArrowRight, User } from 'lucide-react';

interface SlotCardProps {
  slot: Slot;
  currentUserId?: string;
}

export function SlotCard({ slot, currentUserId }: SlotCardProps) {
  const { t } = useTranslation();
  // Identify user role in this slot
  const isReviewer = slot.reviewer_id === currentUserId;
  const isReviewee = slot.reviewee_id === currentUserId;

  const getStatusBadge = () => {
    switch (slot.status) {
      case 'open':
        return <Badge type="success">{t('slots.statusOpen')}</Badge>;
      case 'booked':
        return <Badge type="info">{t('slots.statusBooked')}</Badge>;
      case 'in_progress':
        return <Badge type="warning">{t('slots.statusInProgress')}</Badge>;
      case 'completed':
        return <Badge type="primary">{t('slots.statusCompleted')}</Badge>;
      case 'cancelled':
        return <Badge type="error">{t('slots.statusCancelled')}</Badge>;
      case 'absent':
        return <Badge type="error">{t('slots.statusAbsent')}</Badge>;
      default:
        return <Badge type="info">{slot.status}</Badge>;
    }
  };

  return (
    <Card hover className="flex flex-col gap-3 sm:gap-4 h-full relative font-ibm-plex-mono p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <span className="text-[10px] text-[#B0BEC5] font-extrabold tracking-widest uppercase font-montserrat">
            {isReviewer ? `${t('slots.reviewer')} (YOU)` : isReviewee ? `${t('slots.reviewee')} (YOU)` : `${t('slots.statusOpen')} SLOT`}
          </span>
          <h4 className="text-sm sm:text-base font-extrabold text-white truncate font-montserrat tracking-tight" title={slot.reviewer_project}>
            {slot.reviewer_project}
          </h4>
        </div>
        <div className="flex-shrink-0">{getStatusBadge()}</div>
      </div>

      <div className="flex flex-col gap-2 sm:gap-2.5 text-xs text-[#B0BEC5] py-2 sm:py-2.5 border-y-2 border-black/30 my-1">
        <div className="flex items-center gap-2 min-w-0">
          <Calendar className="h-4 w-4 text-[#38C9E6] flex-shrink-0" />
          <span className="truncate font-bold text-white text-xs">{formatDateTime(slot.start_time)}</span>
        </div>

        <div className="flex items-center gap-3 sm:gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Laptop className="h-4 w-4 text-[#cdbdff] flex-shrink-0" />
            <span className="text-xs">{slot.is_online ? 'Online' : 'Offline'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-[#ffd740] flex-shrink-0" />
            <span className="uppercase font-extrabold text-[11px] text-[#ffd740]">{slot.campus}</span>
          </div>
        </div>

        {slot.reviewer && (
          <div className="flex items-center gap-2 text-[#B0BEC5] min-w-0">
            <User className="h-4 w-4 text-[#38C9E6] flex-shrink-0" />
            <span className="truncate text-xs">{`${t('slots.reviewer')}: `}<strong className="text-white font-extrabold">{slot.reviewer.school21_login}</strong> {slot.reviewer.telegram_username ? `(@${slot.reviewer.telegram_username})` : ''}</span>
          </div>
        )}
        
        {slot.reviewee_project && (
          <div className="flex items-center gap-2 text-[#B0BEC5] min-w-0 mt-1">
            <User className="h-4 w-4 text-[#43E8A0] flex-shrink-0" />
            <span className="truncate text-xs">{`${t('slots.reviewee')}: `}<strong className="text-white font-extrabold">{slot.reviewee ? slot.reviewee.school21_login : t('common.noData')}</strong> {slot.reviewee?.telegram_username ? `(@${slot.reviewee.telegram_username})` : ''} <span className="text-[#B0BEC5] ml-1">({slot.reviewee_project})</span></span>
          </div>
        )}
      </div>

      <div className="mt-auto pt-2 flex justify-end">
        <Link
          to={`/slots/${slot.id}`}
          className="inline-flex items-center gap-2 text-xs font-black text-[#38C9E6] hover:text-[#43E8A0] uppercase tracking-widest group transition-all duration-150 font-montserrat min-h-[44px] sm:min-h-0"
        >
          {t('common.search')} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </Card>
  );
}
export default SlotCard;
