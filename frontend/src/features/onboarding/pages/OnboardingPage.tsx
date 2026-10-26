import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { onboardingService } from '@/features/onboarding/api';
import { useAuthStore } from '@/features/auth/store';
import { Button, Card, Badge, Spinner, DotField } from '@/shared/ui';
import { triggerToast } from '@/shared/stores/toast';
import { Sparkles, ArrowRight, Languages, Compass } from 'lucide-react';

const TRACKS = ['Web', 'Mobile', 'GameDev', 'DataScience', 'DevOps', 'Blockchain'];
const LANGUAGES = [
  "O'zbek",
  'Русский',
  'English',
  'Français',
  'Deutsch',
  'Español',
  'Türkçe',
  'العربية',
  'فarسی',
  '中文',
];

export default function OnboardingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setOnboardingDone = useAuthStore((state) => state.setOnboardingDone);

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);

  // States
  const [coreProgram, setCoreProgram] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<string>('');
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [submitLoading, setSubmitLoading] = useState(false);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const trackData = await onboardingService.getTrack();
        setCoreProgram(trackData.core_program);
        if (trackData.main_track) {
          setSelectedTrack(trackData.main_track);
        }
      } catch (err) {
        console.error('Failed to pre-populate onboarding track state', err);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  const handleConfirmTrack = async () => {
    if (!selectedTrack) {
      triggerToast(t('onboarding.errors.noTrack'), 'error');
      return;
    }

    setSubmitLoading(true);
    try {
      await onboardingService.confirmTrack(selectedTrack);
      triggerToast(t('onboarding.success.trackConfirmed'), 'success');
      setStep(2);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || t('onboarding.errors.actionFailed');
      triggerToast(detail, 'error');
    } finally {
      setSubmitLoading(false);
    }
  };

  const toggleLanguage = (lang: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  const handleConfirmLanguages = async () => {
    if (selectedLanguages.length === 0) {
      triggerToast(t('onboarding.errors.noLanguage'), 'error');
      return;
    }

    setSubmitLoading(true);
    try {
      const response = await onboardingService.confirmLanguages(selectedLanguages);
      if (response.onboarding_done) {
        setOnboardingDone(true);
        triggerToast(t('onboarding.success.completed'), 'success');
        navigate('/dashboard');
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || t('onboarding.errors.actionFailed');
      triggerToast(detail, 'error');
    } finally {
      setSubmitLoading(false);
    }
  };

  if (loading) {
    return <Spinner fullScreen />;
  }

  return (
    <div className="min-h-screen bg-[#1E2A38] flex items-center justify-center p-4 relative overflow-hidden font-ibm-plex-mono text-white">
      {/* Interactive Dot Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <DotField
          dotRadius={1.5}
          dotSpacing={14}
          bulgeStrength={67}
          glowRadius={160}
          sparkle={false}
          waveAmplitude={0}
          cursorRadius={500}
          cursorForce={0.1}
          bulgeOnly
          gradientFrom="rgba(56, 201, 230, 0.25)"
          gradientTo="rgba(67, 232, 160, 0.18)"
          glowColor="rgba(56, 201, 230, 0.1)"
        />
      </div>

      {/* Visual accents */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#38C9E6]/5 rounded-full pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#43E8A0]/5 rounded-full pointer-events-none" />

      <Card hover={false} className="w-full max-w-lg p-4 sm:p-6 lg:p-8 border-2 border-black bg-[#2A3442] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] sm:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative z-10 animate-fade-in rounded-3xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 sm:mb-8 border-b-2 border-black pb-3 sm:pb-4 gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <Sparkles className="h-5 w-5 text-[#38C9E6] shrink-0" />
            <h1 className="text-sm sm:text-lg font-black text-white font-montserrat uppercase tracking-tight truncate">{t('onboarding.title')}</h1>
          </div>
          <span className="text-[10px] sm:text-xs uppercase tracking-wider font-extrabold text-[#B0BEC5] font-montserrat shrink-0">
            {t('onboarding.step')} {step} / 2
          </span>
        </div>

        {step === 1 ? (
          /* Step 1: Yo'nalishni tasdiqlash */
          <div className="flex flex-col gap-4 sm:gap-6">
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2 text-[#43E8A0]">
                <Compass className="h-5 w-5 flex-shrink-0" />
                <h2 className="text-sm sm:text-base font-black uppercase tracking-tight font-montserrat">{t('onboarding.track.title')}</h2>
              </div>
              <p className="text-xs text-[#B0BEC5] leading-relaxed">
                {t('onboarding.track.description')}{' '}
                <strong className="text-white bg-[#34495E] px-2 py-0.5 border border-black rounded-md break-words">{coreProgram || 'CORE'}</strong>
              </p>
            </div>

            {/* Track grid — 1 col on very small, 2 col on sm+ */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {TRACKS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setSelectedTrack(t)}
                  className={`min-h-11 p-3 sm:p-4 rounded-xl border-2 border-black text-xs font-black uppercase tracking-wider transition-all text-left flex items-center justify-between cursor-pointer font-montserrat shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[1px]
                    ${
                      selectedTrack === t
                        ? 'bg-[#38C9E6] text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]'
                        : 'bg-[#34495E] text-[#B0BEC5] hover:text-white hover:bg-gray-600/30'
                    }
                  `}
                >
                  <span>{t}</span>
                  {selectedTrack === t && (
                    <span className="h-2.5 w-2.5 rounded-full bg-black flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>

            <Button
              variant="primary"
              className="w-full mt-2 sm:mt-4 font-montserrat uppercase font-extrabold tracking-wider text-xs text-black"
              onClick={handleConfirmTrack}
              disabled={submitLoading || !selectedTrack}
            >
              {t('onboarding.track.nextBtn')} <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          /* Step 2: Language Preference */
          <div className="flex flex-col gap-4 sm:gap-6">
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2 text-[#cdbdff]">
                <Languages className="h-5 w-5 flex-shrink-0" />
                <h2 className="text-sm sm:text-base font-black uppercase tracking-tight font-montserrat">{t('onboarding.languages.title')}</h2>
              </div>
              <p className="text-xs text-[#B0BEC5] leading-relaxed">
                {t('onboarding.languages.description')}
              </p>
            </div>

            {/* Selected pill counters */}
            <div className="flex flex-wrap gap-1.5 p-3 rounded-xl bg-[#34495E] border-2 border-black min-h-[48px] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              {selectedLanguages.length === 0 ? (
                <span className="text-xs text-[#B0BEC5] select-none font-bold">{t('onboarding.languages.noneSelected')}</span>
              ) : (
                selectedLanguages.map((l) => (
                  <Badge key={l} type="primary">{l}</Badge>
                ))
              )}
            </div>

            {/* Language grid — 2 col mobile, 3 col on sm+ */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3 max-h-48 overflow-y-auto pr-1">
              {LANGUAGES.map((l) => {
                const isSelected = selectedLanguages.includes(l);
                return (
                  <button
                    key={l}
                    type="button"
                    onClick={() => toggleLanguage(l)}
                    className={`min-h-11 px-3 py-2.5 rounded-xl border-2 border-black text-xs font-black uppercase tracking-wider select-none transition-all cursor-pointer font-montserrat shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[0.5px]
                      ${
                        isSelected
                          ? 'bg-[#43E8A0] text-black shadow-none'
                          : 'bg-[#34495E] text-[#B0BEC5] hover:text-white hover:bg-gray-600/30'
                      }
                    `}
                  >
                    {l}
                  </button>
                );
              })}
            </div>

            {/* Action buttons — stacked on mobile, side-by-side on sm+ */}
            <div className="flex flex-col sm:flex-row gap-3 mt-2 sm:mt-4">
              <Button
                variant="ghost"
                className="w-full sm:flex-1 font-montserrat uppercase font-extrabold tracking-wider text-xs border-2 border-transparent hover:border-black"
                onClick={() => setStep(1)}
                disabled={submitLoading}
              >
                Orqaga
              </Button>
              <Button
                variant="primary"
                className="w-full sm:flex-1 font-montserrat uppercase font-extrabold tracking-wider text-xs text-black"
                onClick={handleConfirmLanguages}
                disabled={submitLoading || selectedLanguages.length === 0}
              >
                Onbordingni yakunlash
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
