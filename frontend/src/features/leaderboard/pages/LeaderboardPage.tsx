import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLeaderboard } from '@/features/leaderboard/hooks';
import { Card, Skeleton, PageHeader, EmptyState, Button } from '@/shared/ui';
import { Trophy, Zap, BookOpen, GraduationCap, Medal, AlertTriangle, RefreshCw } from 'lucide-react';

type TabType = 'xp' | 'taught' | 'learned';

export default function LeaderboardPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('xp');
  const {
    mostXP, mostTaught, mostLearned,
    isLoadingXP, isLoadingTaught, isLoadingLearned,
    isErrorXP, isErrorTaught, isErrorLearned,
    refetchXP, refetchTaught, refetchLearned,
  } = useLeaderboard();

  // Pick data and loading flag matching active tab
  const getTabData = () => {
    switch (activeTab) {
      case 'xp':
        return { data: mostXP, loading: isLoadingXP, isError: isErrorXP, refetch: refetchXP, suffix: 'XP' };
      case 'taught':
        return { data: mostTaught, loading: isLoadingTaught, isError: isErrorTaught, refetch: refetchTaught, suffix: t('leaderboard.suffix.times') };
      case 'learned':
        return { data: mostLearned, loading: isLoadingLearned, isError: isErrorLearned, refetch: refetchLearned, suffix: t('leaderboard.suffix.times') };
    }
  };

  const { data: rankedList = [], loading, isError, refetch, suffix } = getTabData();

  const getRankBadgeColors = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-[#ffd740] text-black border-black';
      case 2:
        return 'bg-[#cdbdff] text-black border-black';
      case 3:
        return 'bg-[#FF9B9B] text-black border-black';
      default:
        return 'bg-[#34495E] text-white border-black';
    }
  };

  const tabs = [
    { key: 'xp' as TabType, label: t('leaderboard.tabs.xp'), icon: Zap },
    { key: 'taught' as TabType, label: 'Ko\'p o\'rgatganlar', icon: GraduationCap },
    { key: 'learned' as TabType, label: 'Ko\'p o\'rganganlar', icon: BookOpen },
  ];

  return (
    <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
      <PageHeader
        title={t('leaderboard.title')}
        subtitle={t('leaderboard.subtitle')}
        icon={Trophy}
        iconClassName="text-[#ffd740]"
      />

      {/* Tabs list — scrollable on mobile */}
      <div className="flex border-b-2 border-black pb-3 gap-2 overflow-x-auto scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider font-montserrat border-2 select-none transition-all duration-150 whitespace-nowrap cursor-pointer min-h-11
                ${
                  isActive
                    ? 'bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] border-black text-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]'
                    : 'bg-transparent border-transparent text-[#B0BEC5] hover:text-white hover:bg-[#34495E]/50'
                }
              `}
            >
              <Icon className="h-4 w-4 flex-shrink-0" /> <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Error state */}
      {isError ? (
        <Card className="flex flex-col items-center justify-center py-12 gap-4 text-center">
          <AlertTriangle className="h-10 w-10 text-[#FF9B9B]" />
          <h3 className="text-sm font-extrabold text-[#FF9B9B] font-montserrat uppercase">
            {t('leaderboard.errors.loadTitle')}
          </h3>
          <p className="text-xs text-[#B0BEC5]">
            {t('leaderboard.errors.loadDesc')}
          </p>
          <Button variant="primary" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" /> {t('leaderboard.reload')}
          </Button>
        </Card>
      ) : loading ? (
        <div className="flex flex-col gap-4 sm:gap-5">
          {/* Top Rank spotlights skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 sm:p-6 flex flex-col items-center text-center border-2 border-black bg-[#2A3442] rounded-3xl shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] gap-3 sm:gap-4">
                <Skeleton variant="circle" className="h-10 w-10" />
                <Skeleton variant="text" className="w-[50%] h-4" />
                <Skeleton variant="text" className="w-[30%] h-3" />
                <Skeleton variant="rect" className="w-full h-8 rounded-xl" />
              </div>
            ))}
          </div>
          {/* List items skeleton */}
          <div className="border-2 border-black bg-[#2A3442] rounded-3xl divide-y-2 divide-black">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 sm:p-4 px-4 sm:px-6 gap-3 sm:gap-4">
                <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                  <Skeleton variant="rect" className="h-8 w-8 rounded-lg flex-shrink-0" />
                  <div className="flex flex-col gap-2 flex-1 min-w-0">
                    <Skeleton variant="text" className="w-full h-4" />
                    <Skeleton variant="text" className="w-1/4 h-2.5" />
                  </div>
                </div>
                <Skeleton variant="text" className="w-16 h-4 flex-shrink-0" />
              </div>
            ))}
          </div>
        </div>
      ) : rankedList.length === 0 ? (
        <EmptyState
          title={t('leaderboard.empty.title')}
          description={t('leaderboard.empty.desc')}
          icon={<Medal className="h-7 w-7" />}
        />
      ) : (
        <div className="flex flex-col gap-4 sm:gap-5">
          {/* Top Rank spotlights */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 lg:gap-6 mb-2">
            {rankedList.slice(0, 3).map((item) => (
              <Card
                key={item.user_id}
                className={`p-3.5 sm:p-4 lg:p-6 flex flex-col items-center text-center relative overflow-hidden
                  ${item.rank === 1 ? 'bg-gradient-to-br from-[#ffd740]/25 to-[#ffd740]/5' : ''}
                `}
              >
                {/* Visual rank medal */}
                <div
                  className={`h-10 w-10 rounded-xl flex items-center justify-center font-extrabold text-sm border-2 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] mb-3 sm:mb-4 font-montserrat
                    ${getRankBadgeColors(item.rank)}
                  `}
                >
                  {item.rank}
                </div>

                {/* Information */}
                <span className="text-sm sm:text-base font-extrabold text-white truncate max-w-full font-montserrat tracking-tight">
                  @{item.first_name || t('leaderboard.student')}
                </span>
                <span className="text-[10px] text-[#B0BEC5] font-bold tracking-widest uppercase mt-1">
                  {t('leaderboard.rankSpotlight')}
                </span>

                <div className="mt-3 sm:mt-4 px-2.5 sm:px-4 py-2 rounded-xl bg-[#34495E] border-2 border-black w-full text-center shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                  <span className="text-xs font-black text-[#43E8A0] font-ibm-plex-mono truncate block">
                    {item.value} {suffix}
                  </span>
                </div>
              </Card>
            ))}
          </div>

          {/* Standard rows listings */}
          <Card className="p-0 overflow-hidden">
            <div className="divide-y-2 divide-black">
              {rankedList.map((item) => (
                <div
                  key={item.user_id}
                  className="flex items-center justify-between p-3 sm:p-4 px-3 sm:px-6 hover:bg-[#34495E]/50 transition-colors gap-2 sm:gap-4"
                >
                  <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
                    {/* Rank Indicator */}
                    <div
                      className={`h-7 w-7 sm:h-8 sm:w-8 rounded-lg border-2 flex items-center justify-center text-[10px] sm:text-xs font-black font-ibm-plex-mono shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] flex-shrink-0
                        ${getRankBadgeColors(item.rank)}
                      `}
                    >
                      {item.rank}
                    </div>

                    <div className="flex flex-col min-w-0">
                      <span className="text-xs sm:text-sm font-bold text-white truncate">
                        @{item.first_name || t('leaderboard.student')}
                      </span>
                      <span className="text-[9px] text-[#B0BEC5] font-bold uppercase tracking-wider hidden sm:block">
                        {t('leaderboard.keyMember')}
                      </span>
                    </div>
                  </div>

                  {/* Value */}
                  <span className="text-[10px] sm:text-xs font-black text-[#38C9E6] font-ibm-plex-mono whitespace-nowrap flex-shrink-0">
                    {item.value} {suffix}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
