import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { slotsService } from '@/features/slots/api';
import { useAuth } from '@/features/auth/hooks';
import { useSlots } from '@/features/slots/hooks';
import { Card, Select, Button, EmptyState, Spinner, Skeleton, Modal } from '@/shared/ui';
import { formatDateTime } from '@/shared/lib/utils';
import { triggerToast } from '@/shared/stores/toast';
import { Search, Calendar, Laptop, MapPin, CheckSquare, Sparkles } from 'lucide-react';

export function SlotSearch() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [selectedProject, setSelectedProject] = useState<string>('');
  const { bookSlot, isBookingSlot } = useSlots();
  const [slotToBook, setSlotToBook] = useState<string | null>(null);

  // Load available in-progress projects the student is currently doing
  const { data: inProgressData, isLoading: isLoadingProjects } = useQuery({
    queryKey: ['in-progress-projects-lookup'],
    queryFn: slotsService.getInProgressProjects,
  });

  const inProgressProjects = inProgressData?.projects || [];

  // Search matching active open slots anonymously
  const { data: results = [], isLoading: isSearching, refetch } = useQuery({
    queryKey: ['slots-anonymous-search', selectedProject],
    queryFn: () => slotsService.searchSlots(selectedProject),
    enabled: !!selectedProject,
  });

  const handleBook = async (slotId: string) => {
    if (user && user.peer_points < 1) {
      triggerToast(t('slots.search.errNotEnoughPoints'), 'error');
      return;
    }
    setSlotToBook(slotId);
  };

  const handleConfirmBook = async () => {
    if (!slotToBook) return;
    const slotId = slotToBook;
    setSlotToBook(null);

    try {
      await bookSlot({ id: slotId, project: selectedProject });
      refetch();
    } catch (_e) {
      // handled by hook
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left column: Selection card */}
        <div className="lg:col-span-1">
          <Card className="p-4 sm:p-6 flex flex-col gap-4 sm:gap-5">
            <div className="flex items-center gap-2 border-b-2 border-black pb-4 text-[#38C9E6]">
              <Sparkles className="h-5 w-5 fill-[#38C9E6]/10" />
              <h3 className="text-xs uppercase font-montserrat font-extrabold tracking-wider">{t('slots.search.selectProjectTitle')}</h3>
            </div>

            {isLoadingProjects ? (
              <div className="py-4 text-center">
                <Spinner size="sm" />
              </div>
            ) : inProgressProjects.length === 0 ? (
              <div className="p-3 sm:p-4 bg-[#FF9B9B] border-2 border-black text-xs text-black font-semibold rounded-xl leading-relaxed shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                {t('slots.search.noActiveProjects')}
              </div>
            ) : (
              <Select
                label={t('slots.search.currentProjectLabel')}
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                <option value="" disabled className="bg-[#34495E]">{t('slots.form.selectProject')}</option>
                {inProgressProjects.map((proj) => (
                  <option key={proj.id || proj.title} value={proj.title} className="bg-[#34495E] text-white font-medium">
                    {proj.title}
                  </option>
                ))}
              </Select>
            )}

            {/* Points balance information */}
            {user && (
              <div className="mt-2 p-3 sm:p-4 rounded-xl bg-[#34495E] border-2 border-black flex justify-between items-center text-xs shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <span className="text-[#B0BEC5] font-semibold">{t('slots.search.pointsBalance')}</span>
                <strong className={`font-black text-xs ${user.peer_points >= 1 ? 'text-[#43E8A0]' : 'text-[#FF9B9B]'}`}>
                  {user.peer_points} PT
                </strong>
              </div>
            )}
          </Card>
        </div>

        {/* Right column: Search Results List */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 border-b-2 border-black pb-3">
            <span className="text-sm font-extrabold text-white flex items-center gap-2 font-montserrat tracking-tight">
              <Search className="h-5 w-5 text-[#38C9E6]" /> {t('slots.search.matchingSlots')}
            </span>
            {selectedProject && results.length > 0 && (
              <span className="text-xs text-[#B0BEC5] font-bold tracking-wider leading-none">
                {t('slots.search.totalSlots', { count: results.length })}
              </span>
            )}
          </div>

          {!selectedProject ? (
            <EmptyState
              title={t('slots.search.noProjectSelected')}
              description={t('slots.search.noProjectSelectedDesc')}
              icon={<Search className="h-8 w-8 text-black" />}
            />
          ) : isSearching ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 animate-pulse-subtle">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="p-4 sm:p-5 border-2 border-black bg-[#2A3442] flex flex-col justify-between gap-4 sm:gap-5 rounded-3xl shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <Skeleton variant="circle" className="h-4 w-4" />
                      <Skeleton variant="text" className="w-1/2 h-4" />
                    </div>
                    <div className="flex gap-4 mt-2">
                      <Skeleton variant="text" className="w-16 h-3" />
                      <Skeleton variant="text" className="w-16 h-3" />
                    </div>
                  </div>
                  <div className="pt-2 flex justify-end">
                    <Skeleton variant="rect" className="w-24 h-9 rounded-xl" />
                  </div>
                </div>
              ))}
            </div>
          ) : results.length === 0 ? (
            <EmptyState
              title={t('slots.search.noSlotsFound')}
              description={t('slots.search.noSlotsFoundDesc', { project: selectedProject })}
              icon={<Search className="h-8 w-8 text-black" />}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
              {results.map((res) => (
                <Card key={res.id} className="p-4 sm:p-5 border-2 border-black flex flex-col justify-between gap-4 sm:gap-5 rounded-3xl">
                  <div className="flex flex-col gap-3">
                    {/* Timestamp */}
                    <div className="flex items-center gap-2 text-xs text-white min-w-0">
                      <Calendar className="h-4 w-4 text-[#38C9E6] flex-shrink-0" />
                      <span className="font-bold truncate">{formatDateTime(res.start_time)}</span>
                    </div>

                    {/* Meta specifics */}
                    <div className="flex gap-3 sm:gap-4 text-[10px] text-[#B0BEC5] font-black uppercase tracking-widest mt-1 font-montserrat flex-wrap">
                      <span className="flex items-center gap-1.5">
                        <Laptop className="h-4 w-4 text-[#cdbdff]" /> {res.is_online ? t('slotDetail.online') : t('slotDetail.offline')}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <MapPin className="h-4 w-4 text-[#ffd740]" /> {res.campus}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="pt-2 flex justify-end">
                    <Button
                      variant="primary"
                      onClick={() => handleBook(res.id)}
                      disabled={isBookingSlot}
                      className="w-full sm:w-auto text-xs font-extrabold uppercase tracking-wider"
                    >
                      <CheckSquare className="h-4 w-4 text-black" /> {t('slots.bookBtn')}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {slotToBook && (
        <Modal
          isOpen={!!slotToBook}
          onClose={() => setSlotToBook(null)}
          title={t('slots.search.bookModalTitle')}
        >
          <div className="flex flex-col gap-4">
            <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed">
              {t('slots.search.bookModalDesc')}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end pt-2">
              <button
                type="button"
                onClick={() => setSlotToBook(null)}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-[#34495E] hover:bg-gray-600 text-white font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                onClick={handleConfirmBook}
                className="w-full sm:w-auto px-4 py-2 min-h-[44px] bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] text-black font-extrabold rounded-xl border-2 border-black shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-[3px_3px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] transition-all text-xs tracking-wider uppercase cursor-pointer"
              >
                {t('slots.search.confirmBook')}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
export default SlotSearch;
