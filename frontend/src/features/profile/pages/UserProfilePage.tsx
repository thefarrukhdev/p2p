import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { profileService } from '@/features/profile/api';
import { reviewsService } from '@/features/reviews/api';
import { Card, Avatar, Spinner, Badge, Skeleton } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, ThumbsUp, ThumbsDown, MessageSquare, ShieldAlert } from 'lucide-react';

export default function UserProfilePage() {
  const { t } = useTranslation();
  const { username } = useParams<{ username: string }>();

  // Fetch public representation
  const { data: userPublic, isLoading: isLoadingPublic, isError: isErrorPublic } = useQuery({
    queryKey: ['profile', 'public', username],
    queryFn: () => profileService.getPublicProfile(username || ''),
    enabled: !!username,
  });

  // Fetch client reviews about them
  const userId = userPublic?.id;
  const { data: reviews = [], isLoading: isLoadingReviews } = useQuery({
    queryKey: ['reviews', 'user', userId],
    queryFn: () => reviewsService.getUserReviews(userId || ''),
    enabled: !!userId,
  });

  if (isLoadingPublic) {
    return (
      <div className="flex flex-col gap-6 animate-fade-in font-ibm-plex-mono text-white animate-pulse-subtle">
        {/* Top breadcrumb skeleton */}
        <div>
          <Skeleton variant="text" className="w-32 h-3" />
        </div>

        {/* Header Info Block Skeleton */}
        <div className="p-6 flex flex-col sm:flex-row items-center sm:items-start gap-5 rounded-3xl border-2 border-black bg-[#2A3442] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <Skeleton variant="circle" className="h-24 w-24 flex-shrink-0 animate-pulse" />
          <div className="flex flex-col items-center sm:items-start gap-2.5 w-full">
            <div className="flex items-center gap-2 w-full">
              <Skeleton variant="text" className="w-40 h-5 animate-pulse" />
              <Skeleton variant="rect" className="w-20 h-5 rounded-md animate-pulse" />
            </div>
            <Skeleton variant="text" className="w-24 h-3.5 animate-pulse" />
            <Skeleton variant="text" className="w-[60%] h-3 animate-pulse" />
          </div>
        </div>

        {/* Reviews about this user list skeleton */}
        <div className="flex flex-col gap-4">
          <div className="border-b-2 border-black pb-3">
            <Skeleton variant="text" className="w-48 h-4" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="p-5 border-2 border-black bg-[#2A3442] rounded-2xl flex flex-col gap-3 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <Skeleton variant="text" className="w-1/4 h-4 animate-pulse" />
                <Skeleton variant="text" className="w-full h-8 animate-pulse" />
                <Skeleton variant="rect" className="w-full h-4 rounded-md animate-pulse mt-1" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isErrorPublic || !userPublic) {
    return (
      <div className="py-12 text-center flex flex-col items-center gap-4 font-ibm-plex-mono text-white">
        <p className="text-[#FF9B9B] font-bold">{t('profile.public.not_found', 'Ushbu talaba topilmadi yoki ma‘lumotlarni yuklab bo‘lmadi.')}</p>
        <Link to="/leaderboard" className="text-xs uppercase tracking-wider text-[#38C9E6] underline font-montserrat">
          {t('profile.public.back_to_leaderboard', 'Reyting ro‘yxatiga qaytish')}
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in font-ibm-plex-mono text-white">
      {/* Top breadcrumb */}
      <div>
        <Link
          to="/leaderboard"
          className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-[#B0BEC5] hover:text-white transition-colors font-montserrat min-h-[44px] py-2"
        >
          <ChevronLeft className="h-4 w-4" /> {t('profile.public.back_to_leaderboard', 'Reytingga qaytish')}
        </Link>
      </div>

      {/* Header Info Block */}
      <Card hover={false} className="p-4 sm:p-6 flex flex-col sm:flex-row items-center sm:items-start gap-4 sm:gap-5 relative overflow-hidden bg-[#2A3442] border-2 border-black rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
        <Avatar src={userPublic.avatar_url} name={userPublic.telegram_username} size="xl" />
        <div className="flex flex-col items-center sm:items-start gap-1 min-w-0 flex-1">
          <div className="flex flex-col sm:flex-row items-center gap-2 text-center sm:text-left">
            <h2 className="text-base sm:text-lg font-black text-white font-montserrat tracking-tight">
              {userPublic.first_name || 'Ism'} {userPublic.last_name || 'Familiya'}
            </h2>
            <Badge type="secondary">{`LEVEL ${userPublic.level}`}</Badge>
          </div>
          <span className="text-xs text-[#38C9E6] font-bold">
            @{userPublic.telegram_username || 'telegram_yo‘q'}
          </span>
          <span className="text-[10px] text-[#B0BEC5] uppercase tracking-wider font-extrabold mt-1 text-center sm:text-left break-words">
            Program: {userPublic.core_program || 'CORE'} • Track: {userPublic.main_track || 'Web'} • Campus: {userPublic.campus || 'Mavjud emas'}
          </span>
          {userPublic.coalition_name && (
            <span className="text-[10px] text-[#cdbdff] font-bold uppercase mt-1 text-center sm:text-left">
              Koalitsiya: {userPublic.coalition_name}
            </span>
          )}
        </div>
      </Card>

      {/* Reviews about this user list */}
      <div className="flex flex-col gap-4">
        <span className="text-sm font-extrabold text-white flex items-center gap-2 border-b-2 border-black pb-3 font-montserrat uppercase tracking-wider">
          <MessageSquare className="h-5 w-5 text-[#38C9E6]" /> {t('profile.reviews.title', 'Ushbu talaba haqida fikrlar (Reviews)')}
        </span>

        {isLoadingReviews ? (
          <Spinner size="sm" />
        ) : reviews.length === 0 ? (
          <Card className="p-8 text-center bg-[#2A3442]/50 text-[#B0BEC5] text-xs border-2 border-black rounded-2xl">
            {t('profile.reviews.empty', 'Hali bu talaba haqida hech qanday fikr-mulohazalar yozib qoldirilmagan.')}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {reviews.map((rev) => (
              <Card key={rev.id} hover={false} className="p-5 border-2 border-black flex flex-col justify-between gap-4 bg-[#2A3442] rounded-2xl shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {rev.is_positive ? (
                      <ThumbsUp className="h-5 w-5 text-[#43E8A0] bg-[#43E8A0]/10 p-1 rounded" />
                    ) : (
                      <ThumbsDown className="h-5 w-5 text-[#FF9B9B] bg-[#FF9B9B]/10 p-1 rounded" />
                    )}
                    <span className={`text-xs font-black uppercase tracking-wider font-montserrat ${rev.is_positive ? 'text-[#43E8A0]' : 'text-[#FF9B9B]'}`}>
                      {rev.is_positive ? t('profile.reviews.positive', 'Ijobiy Fikr') : t('profile.reviews.negative', 'Salbiy Fikr')}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-[#B0BEC5] leading-relaxed italic">
                  "{rev.comment || t('profile.reviews.no_comment', 'Tavsif qoldirilmagan')}"
                </p>

                <div className="text-[9px] text-[#B0BEC5] uppercase tracking-wider font-bold border-t-2 border-black/30 pt-3 flex justify-between font-montserrat">
                  <span>{t('profile.reviews.reviewer', "Baholovchi a'zo")}</span>
                  <span className="text-[#43E8A0] font-black">{t('profile.reviews.saved', 'SAQLANGAN')}</span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

