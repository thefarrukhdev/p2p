import { useTranslation } from 'react-i18next';
import { SlotStatus } from '@/shared/types/api';
import { Check, AlertTriangle } from 'lucide-react';

interface SlotTimelineProps {
  status: SlotStatus;
  actualStart?: string | null;
  actualEnd?: string | null;
}

export function SlotTimeline({ status, actualStart, actualEnd }: SlotTimelineProps) {
  const { t, i18n } = useTranslation();

  const steps = [
    { key: 'created', label: t('slotDetail.stepCreated'), desc: t('slotDetail.stepCreatedDesc') },
    { key: 'booked', label: t('slotDetail.stepBooked'), desc: t('slotDetail.stepBookedDesc') },
    { key: 'in_progress', label: t('slotDetail.stepStarted'), desc: t('slotDetail.stepStartedDesc') },
    { key: 'completed', label: t('slotDetail.stepCompleted'), desc: t('slotDetail.stepCompletedDesc') },
  ];

  const getStepIndex = () => {
    switch (status) {
      case 'open':
        return 0;
      case 'booked':
        return 1;
      case 'in_progress':
        return 2;
      case 'completed':
        return 3;
      case 'cancelled':
      case 'absent':
        return -1;
    }
  };

  const activeIndex = getStepIndex();
  const dateLocale = i18n.language === 'ru' ? 'ru-RU' : i18n.language === 'en' ? 'en-US' : 'uz-UZ';

  return (
    <div className="flex flex-col gap-4 sm:gap-5 p-4 sm:p-5 bg-[#2A3442] border-2 border-black rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-ibm-plex-mono">
      <h3 className="text-xs uppercase font-montserrat font-black tracking-widest text-[#B0BEC5] mb-1 sm:mb-2">
        {t('slotDetail.timelineTitle')}
      </h3>

      {status === 'cancelled' && (
        <div className="p-3 sm:p-4 rounded-2xl bg-[#4A2D2D] border-2 border-black flex items-start gap-3 mb-2 animate-fade-in shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <AlertTriangle className="h-5 w-5 text-[#FF9B9B] flex-shrink-0 mt-0.5" />
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-black text-[#FF9B9B] font-montserrat">{t('slotDetail.cancelledTitle')}</span>
            <span className="text-xs text-[#B0BEC5] leading-relaxed">{t('slotDetail.cancelledDesc')}</span>
          </div>
        </div>
      )}

      {status === 'absent' && (
        <div className="p-3 sm:p-4 rounded-2xl bg-[#4A2D2D] border-2 border-black flex items-start gap-3 mb-2 animate-fade-in shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <AlertTriangle className="h-5 w-5 text-[#FF9B9B] flex-shrink-0 mt-0.5" />
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-black text-[#FF9B9B] font-montserrat">{t('slotDetail.absentTitle')}</span>
            <span className="text-xs text-[#B0BEC5] leading-relaxed">{t('slotDetail.absentDesc')}</span>
          </div>
        </div>
      )}

      <div className="relative border-l-2 border-black ml-3 pl-5 sm:pl-6 space-y-5 sm:space-y-6">
        {steps.map((step, idx) => {
          const isDone = activeIndex >= idx;
          const isCurrent = activeIndex === idx;

          return (
            <div key={step.key} className="relative group">
              <div
                className={`absolute -left-[29px] sm:-left-[33px] top-1.5 h-5 w-5 rounded-lg border-2 border-black flex items-center justify-center transition-all duration-300 shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]
                  ${isDone ? 'bg-gradient-to-br from-[#38C9E6] to-[#43E8A0]' : 'bg-[#34495E]'}`}
              >
                {isDone && <Check className="h-3 w-3 text-black stroke-[3]" />}
              </div>

              <div className="flex flex-col gap-0.5">
                <span
                  className={`text-sm font-black font-montserrat transition-colors duration-150
                    ${isCurrent ? 'text-[#43E8A0]' : isDone ? 'text-white' : 'text-[#B0BEC5]'}`}
                >
                  {step.label}
                </span>
                <span className="text-xs text-[#B0BEC5] leading-relaxed">{step.desc}</span>

                {step.key === 'in_progress' && actualStart && (
                  <span className="text-[10px] font-ibm-plex-mono text-[#38C9E6] mt-1">
                    {t('slotDetail.startTimeLabel')} {new Date(actualStart).toLocaleTimeString(dateLocale)}
                  </span>
                )}
                {step.key === 'completed' && actualEnd && (
                  <span className="text-[10px] font-ibm-plex-mono text-[#cdbdff] mt-1">
                    {t('slotDetail.endTimeLabel')} {new Date(actualEnd).toLocaleTimeString(dateLocale)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
export default SlotTimeline;
