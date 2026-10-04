import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import i18n from '@/shared/lib/i18n';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsService } from '@/features/settings/api';
import { Skeleton, Modal, PageHeader, Card, Button, EmptyState } from '@/shared/ui';
import { triggerToast } from '@/shared/stores/toast';
import { Settings, Languages, Eye, Unlink, Lock, X, ShieldAlert, LogOut, AlertTriangle, RefreshCw } from 'lucide-react';
import { authService } from '@/features/auth/api';
import { useAuthStore } from '@/features/auth/store';

const LANGUAGE_OPTIONS = [
  { value: 'uz', label: "O'zbek" },
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'English' },
];

export default function SettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const logout = useAuthStore((state) => state.logout);

  // Load language and campus configuration details
  const { data: config, isLoading, isError, refetch } = useQuery({
    queryKey: ['settings-page-logs'],
    queryFn: settingsService.getSettings,
  });

  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [showUnlinkModal, setShowUnlinkModal] = useState<boolean>(false);
  const [showLogoutModal, setShowLogoutModal] = useState<boolean>(false);
  const [unlinkPassword, setUnlinkPassword] = useState<string>('');
  const [isUnlinking, setIsUnlinking] = useState<boolean>(false);

  useEffect(() => {
    if (config?.languages && config.languages.length > 0) {
      setSelectedLanguage(config.languages[0]);
    }
  }, [config]);

  // Language update mutation
  const updateLanguageMutation = useMutation({
    mutationFn: (lang: string) => settingsService.updateLanguage(lang),
    onSuccess: () => {
      triggerToast(t('settings.toast.langSaved'), 'success');
      queryClient.invalidateQueries({ queryKey: ['settings-page-logs'] });
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail || t('settings.toast.error');
      triggerToast(detail, 'error');
    },
  });

  const handleLanguageSave = () => {
    if (!selectedLanguage) {
      triggerToast(t('settings.toast.selectLang'), 'error');
      return;
    }
    
    // Change actual UI language
    i18n.changeLanguage(selectedLanguage);
    localStorage.setItem('preferredLanguage', selectedLanguage);
    
    updateLanguageMutation.mutate(selectedLanguage);
  };

  const handleUnlinkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!unlinkPassword) {
      triggerToast(t('settings.toast.enterPassword'), 'error');
      return;
    }

    setIsUnlinking(true);
    try {
      await authService.unlinkTelegram(unlinkPassword);
      triggerToast(t('settings.toast.unlinkSuccess'), 'success');
      setShowUnlinkModal(false);

      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Hisob paroli noto\'g\'ri';
      triggerToast(detail, 'error');
    } finally {
      setIsUnlinking(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
        <PageHeader
          title={t('settings.title')}
          subtitle={t('settings.subtitle')}
          icon={Settings}
        />
        {/* Content skeletons */}
        <div className="flex flex-col gap-4 sm:gap-6 w-full max-w-2xl">
          <div className="bg-[#2A3442] p-4 sm:p-6 rounded-3xl border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4">
            <div className="flex items-center gap-2 border-b-2 border-black/20 pb-3">
              <Skeleton variant="circle" className="h-6 w-6" />
              <Skeleton variant="text" className="w-32 h-4" />
            </div>
            <div className="bg-[#34495E] p-4 rounded-xl border-2 border-black flex flex-col gap-3">
              <Skeleton variant="text" className="w-24 h-3" />
              <div className="flex gap-2 flex-wrap">
                <Skeleton variant="rect" className="w-16 h-7 rounded-lg" />
                <Skeleton variant="rect" className="w-20 h-7 rounded-lg" />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <Skeleton variant="rect" className="w-full h-11 rounded-xl" />
              <Skeleton variant="rect" className="w-full sm:w-24 h-11 rounded-xl" />
            </div>
          </div>
          <div className="bg-[#2A3442] p-4 sm:p-6 rounded-3xl border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4">
            <Skeleton variant="text" className="w-48 h-4" />
            <Skeleton variant="text" className="w-full h-12" />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
        <PageHeader
          title={t('settings.title')}
          subtitle={t('settings.subtitle')}
          icon={Settings}
        />
        <Card className="flex flex-col items-center justify-center py-12 gap-4 text-center">
          <AlertTriangle className="h-10 w-10 text-[#FF9B9B]" />
          <h3 className="text-sm font-extrabold text-[#FF9B9B] font-montserrat uppercase">
            {t('settings.errors.loadTitle')}
          </h3>
          <p className="text-xs text-[#B0BEC5]">
            {t('settings.errors.loadDesc')}
          </p>
          <Button variant="primary" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" /> {t('settings.reload')}
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 sm:gap-6 animate-fade-in font-ibm-plex-mono text-white">
      <PageHeader
        title={t('settings.title')}
        subtitle={t('settings.subtitle')}
        icon={Settings}
      />

      <div className="flex flex-col gap-4 sm:gap-6 w-full max-w-2xl">
        {/* Language preferred section */}
        <Card className="flex flex-col gap-4 sm:gap-5 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
          {/* Section Header */}
          <div className="flex items-center gap-3 border-b-2 border-black pb-3">
            <div className="w-8 h-8 rounded-lg bg-[#38C9E6] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] flex-shrink-0">
              <Languages className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-bold uppercase tracking-wider font-montserrat text-white leading-none">
              {t('settings.language.title')}
            </h2>
          </div>

          {/* Current Active Language */}
          <div className="flex flex-col gap-2 bg-[#34495E] p-3 sm:p-4 rounded-xl border-2 border-black">
            <span className="text-xs uppercase tracking-wider font-bold font-montserrat text-[#38C9E6]">
              {t('settings.language.active')}
            </span>
            <div className="flex mt-1">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold border-2 border-black bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                {LANGUAGE_OPTIONS.find(l => l.value === i18n.language)?.label || i18n.language}
              </span>
            </div>
          </div>

          {/* Interactive select list and primary action block */}
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase tracking-wider font-bold font-montserrat text-[#B0BEC5] mb-1">
              {t('settings.language.add')}
            </label>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
              <div className="relative flex-1 w-full">
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="w-full h-11 px-4 py-2 border-2 border-black rounded-xl bg-[#34495E] text-white font-ibm-plex-mono focus:outline-none focus:ring-2 focus:ring-[#38C9E6] transition-all cursor-pointer"
                >
                  <option value="" disabled className="bg-[#34495E] text-[#B0BEC5]">-- {t('settings.language.select')} --</option>
                  {LANGUAGE_OPTIONS.map((l) => (
                    <option key={l.value} value={l.value} className="bg-[#2A3442] text-white">
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>

              <Button
                variant="primary"
                onClick={handleLanguageSave}
                disabled={updateLanguageMutation.isPending}
                className="w-full sm:w-auto min-h-11"
              >
                {updateLanguageMutation.isPending ? t('settings.language.saving') : t('settings.language.saveBtn')}
              </Button>
            </div>
          </div>
        </Card>

        {/* Security Telegram Connection Unlink */}
        <div className="bg-[#FF9B9B]/10 p-4 sm:p-6 rounded-3xl border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all flex flex-col gap-4">
          {/* Section Header */}
          <div className="flex items-center gap-3 border-b-2 border-black pb-3">
            <div className="w-8 h-8 rounded-lg bg-[#FF9B9B] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] flex-shrink-0">
              <Unlink className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-bold uppercase tracking-wider font-montserrat text-[#FF9B9B] leading-none">
              {t('settings.security.title')}
            </h2>
          </div>

          <div className="flex flex-col gap-4">
            <p className="text-xs text-[#B0BEC5] leading-relaxed">
              {t('settings.security.desc')}
            </p>

            <div className="flex justify-end mt-1">
              <Button
                variant="danger"
                onClick={() => {
                  setUnlinkPassword('');
                  setShowUnlinkModal(true);
                }}
                className="w-full sm:w-auto min-h-11"
              >
                Telegram ulanishini uzish
              </Button>
            </div>
          </div>
        </div>

        {/* Tizimdan Chiqish Section */}
        <Card className="flex flex-col gap-4 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
          {/* Section Header */}
          <div className="flex items-center gap-3 border-b-2 border-black pb-3">
            <div className="w-8 h-8 rounded-lg bg-[#FF9B9B] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] flex-shrink-0">
              <LogOut className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-bold uppercase tracking-wider font-montserrat text-white leading-none">
              {t('settings.logout.title')}
            </h2>
          </div>

          <div className="flex flex-col gap-4">
            <p className="text-xs text-[#B0BEC5] leading-relaxed">
              {t('settings.logout.desc')}
            </p>

            <div className="flex justify-end mt-1">
              <Button
                variant="danger"
                onClick={() => setShowLogoutModal(true)}
                className="w-full sm:w-auto min-h-11"
              >
                Tizimdan chiqish
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Show Logout Confirmation modal */}
      {showLogoutModal && (
        <Modal
          isOpen={showLogoutModal}
          onClose={() => setShowLogoutModal(false)}
          title={t('settings.logoutModal.title')}
        >
          <div className="flex flex-col gap-4">
            <p className="text-xs text-[#B0BEC5] leading-relaxed">
              {t('settings.logoutModal.desc')}
            </p>
            <div className="flex flex-col-reverse sm:flex-row gap-3 justify-end pt-2">
              <Button
                variant="ghost"
                onClick={() => setShowLogoutModal(false)}
                className="w-full sm:w-auto min-h-11"
              >
                Qolish
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  setShowLogoutModal(false);
                  logout();
                }}
                className="w-full sm:w-auto min-h-11"
              >
                Chiqish
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Unlink Modal */}
      {showUnlinkModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-[#2A3442] rounded-3xl p-5 sm:p-8 max-w-md w-full border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4 sm:gap-5 animate-fade-in max-h-[90vh] overflow-y-auto">

            <div className="flex justify-between items-center border-b-2 border-black pb-3">
              <span className="text-base sm:text-lg font-extrabold font-montserrat text-white tracking-tight uppercase">
                {t('settings.unlinkModal.title')}
              </span>
              <button
                onClick={() => setShowUnlinkModal(false)}
                className="w-10 h-10 sm:w-8 sm:h-8 rounded-lg bg-[#34495E] border-2 border-black flex items-center justify-center text-white hover:bg-black hover:text-[#38C9E6] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-start gap-3 p-3 sm:p-4 rounded-xl bg-[#FF9B9B]/10 border-2 border-black">
              <ShieldAlert className="h-6 w-6 text-[#FF9B9B] shrink-0" />
              <div className="flex flex-col gap-1">
                <span className="text-xs font-extrabold text-[#FF9B9B] uppercase tracking-wider font-montserrat">{t('settings.unlinkModal.warning')}</span>
                <p className="text-xs text-[#B0BEC5] leading-relaxed">
                  {t('settings.unlinkModal.desc')}
                </p>
              </div>
            </div>

            <form onSubmit={handleUnlinkSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs uppercase tracking-wider font-bold font-montserrat text-[#B0BEC5]">
                  {t('settings.unlinkModal.passwordLabel')}
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={unlinkPassword}
                    onChange={(e) => setUnlinkPassword(e.target.value)}
                    placeholder={t('settings.unlinkModal.passwordPlaceholder')}
                    className="h-11 w-full rounded-xl bg-[#34495E] border-2 border-black pl-10 pr-3 text-sm text-white placeholder:text-[#B0BEC5] focus:outline-none focus:ring-2 focus:ring-[#38C9E6] transition-all"
                    autoFocus
                  />
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#B0BEC5]" />
                </div>
              </div>

              <div className="flex flex-col-reverse sm:flex-row gap-3 mt-2">
                <Button
                  variant="ghost"
                  onClick={() => setShowUnlinkModal(false)}
                  disabled={isUnlinking}
                  className="w-full sm:flex-1 min-h-11"
                >
                  Bekor qilish
                </Button>
                <Button
                  variant="danger"
                  onClick={() => handleUnlinkSubmit(new Event('submit') as unknown as React.FormEvent)}
                  disabled={isUnlinking || !unlinkPassword}
                  className="w-full sm:flex-1 min-h-11"
                >
                  {isUnlinking ? t('settings.unlinkModal.unlinking') : t('settings.unlinkModal.confirmBtn')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
