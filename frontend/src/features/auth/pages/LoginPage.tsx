import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/features/auth/hooks';
import { useAuthStore } from '@/features/auth/store';
import { DotField, LanguageSwitcher, Spinner } from '@/shared/ui';
import {
  Zap,
  User as UserIcon,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  Key,
  Send,
  Users,
  Trophy,
  CalendarDays,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { triggerToast } from '@/shared/stores/toast';

const loginSchema = z.object({
  login: z.string().min(2, "Login kamida 2 ta belgidan iborat bo'lishi kerak"),
  password: z.string().min(4, "Parol kamida 4 ta belgidan iborat bo'lishi kerak"),
});

const verifySchema = z.object({
  code: z.string().length(6, "Kod roppa-rosa 6 ta raqam bo'lishi kerak"),
});

type LoginFormValues = z.infer<typeof loginSchema>;
type VerifyFormValues = z.infer<typeof verifySchema>;

export default function LoginPage() {
  const { t } = useTranslation();
  const { login, isLoggingIn, loginData, verifyCode, isVerifyingCode } = useAuth();
  const { setTokens } = useAuthStore();

  const [showOtp, setShowOtp] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);

  const SLIDES = [
    {
      icon: Users,
      badge: '01 / REVIEWS',
      title: t('login.slides.p2p.title'),
      description: t('login.slides.p2p.desc'),
      gradient: 'from-[#38C9E6] to-[#43E8A0]',
    },
    {
      icon: Trophy,
      badge: '02 / GAMIFICATION',
      title: t('login.slides.gamification.title'),
      description: t('login.slides.gamification.desc'),
      gradient: 'from-[#FFB547] to-[#FF6B6B]',
    },
    {
      icon: CalendarDays,
      badge: '03 / SCHEDULING',
      title: t('login.slides.slots.title'),
      description: t('login.slides.slots.desc'),
      gradient: 'from-[#8B5CF6] to-[#38C9E6]',
    },
  ];

  // Auto carousel rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [SLIDES.length]);

  const {
    register: loginRegister,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const {
    register: verifyRegister,
    handleSubmit: handleVerifySubmit,
    formState: { errors: verifyErrors },
  } = useForm<VerifyFormValues>({
    resolver: zodResolver(verifySchema),
  });

  const onLoginSubmit = (values: LoginFormValues) => {
    login(values, {
      onSuccess: (data) => {
        if (data.status === 'need_telegram') {
          setShowOtp(true);
          triggerToast(t('login.toast.otp'), 'info');
        } else if (data.status === 'ok' && data.access_token) {
          setTokens(data.access_token, data.refresh_token as string, data.onboarding_done);
          triggerToast(t('login.toast.success'), 'success');
        }
      },
    });
  };

  const onVerifySubmit = (values: VerifyFormValues) => {
    if (!loginData?.temp_token) {
      triggerToast(t('login.toast.sessionExpired'), 'error');
      setShowOtp(false);
      return;
    }

    verifyCode({
      temp_token: loginData.temp_token,
      code: values.code,
    });
  };

  return (
    <div className="min-h-screen bg-[#141E28] text-white flex flex-col justify-between relative overflow-hidden font-sans select-none">
      {/* Interactive Global Particle Canvas Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <DotField
          dotRadius={1.5}
          dotSpacing={16}
          bulgeStrength={55}
          glowRadius={150}
          sparkle={false}
          waveAmplitude={0}
          cursorRadius={450}
          cursorForce={0.12}
          bulgeOnly
          gradientFrom="rgba(56, 201, 230, 0.22)"
          gradientTo="rgba(67, 232, 160, 0.16)"
          glowColor="rgba(56, 201, 230, 0.12)"
        />
      </div>

      {/* Ambient background glow orbs */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-[#38C9E6]/10 rounded-full blur-[160px] pointer-events-none z-0" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-[#43E8A0]/10 rounded-full blur-[180px] pointer-events-none z-0" />

      {/* Top Navigation Bar */}
      <header className="relative z-20 w-full max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] p-0.5 shadow-lg shadow-[#38C9E6]/20 flex items-center justify-center">
            <div className="h-full w-full bg-[#182430] rounded-[10px] flex items-center justify-center">
              <Zap className="h-5 w-5 text-[#38C9E6]" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-black tracking-tight text-white font-montserrat flex items-center gap-2">
              P2P Platform
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#43E8A0]/15 text-[#43E8A0] border border-[#43E8A0]/30 font-ibm-plex-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-[#43E8A0] animate-pulse" />
                LIVE
              </span>
            </span>
            <span className="text-[11px] text-[#7E92A2] font-ibm-plex-mono">
              Peer Learning Workspace
            </span>
          </div>
        </div>

        {/* Language selector in glass style */}
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
        </div>
      </header>

      {/* Main Split Section */}
      <main className="relative z-10 w-full max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-6 my-auto flex-grow flex items-center">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-center">
          {/* Left Column: Visual Showcase & Benefits */}
          <div className="hidden lg:flex lg:col-span-6 flex-col justify-center space-y-8 pr-4">
            {/* Pill Tag */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md w-fit">
              <Sparkles className="w-4 h-4 text-[#38C9E6]" />
              <span className="text-xs font-semibold text-[#B0BEC5] tracking-wide uppercase font-montserrat">
                {t('login.badge')}
              </span>
            </div>

            {/* Hero Heading */}
            <div className="space-y-4">
              <h1 className="text-4xl xl:text-5xl font-black font-montserrat tracking-tight leading-[1.15]">
                {t('login.heroTitle')}
              </h1>
              <p className="text-[#8FA2B2] text-base xl:text-lg leading-relaxed max-w-lg font-normal">
                {t('login.heroSubtitle')}
              </p>
            </div>

            {/* Slides / Features Cards */}
            <div className="relative min-h-[160px] bg-[#1E2B38]/60 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-xl">
              {SLIDES.map((slide, idx) => {
                const SlideIcon = slide.icon;
                const isActive = idx === currentSlide;
                return (
                  <div
                    key={slide.badge}
                    className={`transition-all duration-500 ease-out ${
                      isActive
                        ? 'opacity-100 translate-y-0 relative'
                        : 'opacity-0 translate-y-4 absolute inset-0 pointer-events-none p-6'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className={`p-2.5 rounded-xl bg-gradient-to-br ${slide.gradient} text-black font-bold shadow-md`}>
                        <SlideIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <span className="text-[10px] font-mono tracking-wider font-bold text-[#38C9E6] block">
                          {slide.badge}
                        </span>
                        <h3 className="text-lg font-bold text-white font-montserrat">
                          {slide.title}
                        </h3>
                      </div>
                    </div>
                    <p className="text-sm text-[#9BB0C1] leading-relaxed pl-12">
                      {slide.description}
                    </p>
                  </div>
                );
              })}

              {/* Progress Indicators */}
              <div className="flex items-center gap-2 pt-4 mt-2 border-t border-white/5">
                {SLIDES.map((_, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setCurrentSlide(idx)}
                    className={`h-1.5 rounded-full transition-all duration-300 cursor-pointer ${
                      idx === currentSlide
                        ? 'w-8 bg-gradient-to-r from-[#38C9E6] to-[#43E8A0]'
                        : 'w-2 bg-white/15 hover:bg-white/30'
                    }`}
                    aria-label={`Slide ${idx + 1}`}
                  />
                ))}
              </div>
            </div>

            {/* Value Highlights */}
            <div className="grid grid-cols-3 gap-4 pt-2">
              <div className="flex items-center gap-2.5 text-xs text-[#9BB0C1] font-mono">
                <CheckCircle2 className="w-4 h-4 text-[#43E8A0] shrink-0" />
                <span>Peer Reviews</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-[#9BB0C1] font-mono">
                <ShieldCheck className="w-4 h-4 text-[#38C9E6] shrink-0" />
                <span>2FA Xavfsiz</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-[#9BB0C1] font-mono">
                <Zap className="w-4 h-4 text-[#FFB547] shrink-0" />
                <span>Real-vaqtda</span>
              </div>
            </div>
          </div>

          {/* Right Column: Premium Login Form Card */}
          <div className="lg:col-span-6 flex justify-center lg:justify-end">
            <div className="w-full max-w-[460px] bg-[#1E2B38]/90 backdrop-blur-2xl border border-white/12 rounded-3xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.6)] p-6 sm:p-9 relative overflow-hidden transition-all">
              {/* Top ambient highlight line */}
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#38C9E6] to-transparent opacity-70" />

              {/* Card Header */}
              <div className="mb-6">
                <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-montserrat">
                  {t('login.welcome')}
                </h2>
                <p className="text-xs sm:text-sm text-[#8EA1B2] mt-2 leading-relaxed">
                  {t('login.description')}
                </p>
              </div>

              {!showOtp ? (
                /* Main Login Form */
                <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="space-y-4">
                  {/* Username / Login Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#B0C0CE] font-montserrat uppercase tracking-wider block">
                      {t('login.loginLabel')}
                    </label>
                    <div
                      className={`relative flex items-center rounded-xl bg-[#17222D] border transition-all ${
                        loginErrors.login
                          ? 'border-[#FF6B6B] ring-2 ring-[#FF6B6B]/20'
                          : 'border-white/10 focus-within:border-[#38C9E6] focus-within:ring-2 focus-within:ring-[#38C9E6]/25'
                      }`}
                    >
                      <div className="pl-3.5 pr-2 text-[#718596]">
                        <UserIcon className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        disabled={isLoggingIn}
                        autoCapitalize="none"
                        autoComplete="username"
                        placeholder={t('login.loginPlaceholder')}
                        {...loginRegister('login')}
                        className="w-full bg-transparent py-3 pr-3 text-sm text-white placeholder-[#506373] focus:outline-none font-ibm-plex-mono font-medium"
                      />
                    </div>
                    {loginErrors.login && (
                      <p className="text-[11px] text-[#FF6B6B] font-semibold pl-1">
                        {loginErrors.login.message}
                      </p>
                    )}
                  </div>

                  {/* Password Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#B0C0CE] font-montserrat uppercase tracking-wider block">
                      {t('login.passwordLabel')}
                    </label>
                    <div
                      className={`relative flex items-center rounded-xl bg-[#17222D] border transition-all ${
                        loginErrors.password
                          ? 'border-[#FF6B6B] ring-2 ring-[#FF6B6B]/20'
                          : 'border-white/10 focus-within:border-[#38C9E6] focus-within:ring-2 focus-within:ring-[#38C9E6]/25'
                      }`}
                    >
                      <div className="pl-3.5 pr-2 text-[#718596]">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type={showPassword ? 'text' : 'password'}
                        disabled={isLoggingIn}
                        autoComplete="current-password"
                        placeholder={t('login.passwordPlaceholder')}
                        {...loginRegister('password')}
                        className="w-full bg-transparent py-3 pr-3 text-sm text-white placeholder-[#506373] focus:outline-none font-ibm-plex-mono font-medium"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="pr-3.5 text-[#718596] hover:text-white transition-colors cursor-pointer"
                        tabIndex={-1}
                        aria-label="Toggle password visibility"
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    {loginErrors.password && (
                      <p className="text-[11px] text-[#FF6B6B] font-semibold pl-1">
                        {loginErrors.password.message}
                      </p>
                    )}
                  </div>

                  {/* Action Button */}
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={isLoggingIn}
                      className="w-full h-12 bg-gradient-to-r from-[#38C9E6] via-[#3FE0AB] to-[#43E8A0] text-[#121B26] font-extrabold text-sm rounded-xl shadow-lg shadow-[#38C9E6]/25 hover:shadow-[#38C9E6]/40 hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                    >
                      {isLoggingIn ? (
                        <>
                          <Spinner size="sm" className="text-[#121B26]" />
                          <span>{t('login.loggingIn')}</span>
                        </>
                      ) : (
                        <>
                          <span>{t('login.loginBtn')}</span>
                          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                /* Telegram OTP Verification Form */
                <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-5">
                  <div className="bg-[#17222D] border border-[#38C9E6]/30 p-4 rounded-2xl flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-[#38C9E6]">
                      <Send className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold font-montserrat uppercase tracking-wider">
                        {t('login.otpTitle')}
                      </span>
                    </div>
                    <p className="text-xs text-[#8FA2B2] leading-relaxed">
                      {t('login.otpDescription')}
                    </p>
                    {loginData?.bot_url && (
                      <a
                        href={loginData.bot_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center gap-2 py-2 px-3 text-xs font-bold text-[#141E28] bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] rounded-lg hover:opacity-95 transition-all mt-1"
                      >
                        <Send className="w-3.5 h-3.5" />
                        {t('login.openBot')}
                      </a>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#B0C0CE] font-montserrat uppercase tracking-wider block">
                      {t('login.verificationCode')}
                    </label>
                    <div
                      className={`relative flex items-center rounded-xl bg-[#17222D] border transition-all ${
                        verifyErrors.code
                          ? 'border-[#FF6B6B] ring-2 ring-[#FF6B6B]/20'
                          : 'border-white/10 focus-within:border-[#38C9E6] focus-within:ring-2 focus-within:ring-[#38C9E6]/25'
                      }`}
                    >
                      <input
                        type="text"
                        maxLength={6}
                        autoFocus
                        disabled={isVerifyingCode}
                        placeholder="000000"
                        {...verifyRegister('code')}
                        className="w-full bg-transparent py-3 px-4 text-center text-lg tracking-[0.5em] text-white placeholder-[#506373] focus:outline-none font-ibm-plex-mono font-bold"
                      />
                    </div>
                    {verifyErrors.code && (
                      <p className="text-[11px] text-[#FF6B6B] font-semibold pl-1 text-center">
                        {verifyErrors.code.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-3 pt-2">
                    <button
                      type="submit"
                      disabled={isVerifyingCode}
                      className="w-full h-12 bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] text-[#121B26] font-extrabold text-sm rounded-xl shadow-lg shadow-[#38C9E6]/25 hover:shadow-[#38C9E6]/40 hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isVerifyingCode ? (
                        <>
                          <Spinner size="sm" className="text-[#121B26]" />
                          <span>{t('login.verifyingOtp')}</span>
                        </>
                      ) : (
                        <>
                          <Key className="w-4 h-4" />
                          <span>{t('login.verifyOtp')}</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowOtp(false)}
                      className="w-full py-2 text-xs font-bold text-[#8FA2B2] hover:text-white transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      {t('login.goBack')}
                    </button>
                  </div>
                </form>
              )}

              {/* Bottom Support Section */}
              <div className="mt-6 pt-5 border-t border-white/8 flex items-start gap-3">
                <HelpCircle className="w-4 h-4 text-[#718596] shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-white block">
                    {t('login.howToBegin')}
                  </span>
                  <p className="text-[11px] text-[#7E92A2] leading-relaxed">
                    {t('login.schoolLinkDesc1')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer copyright */}
      <footer className="relative z-20 w-full max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-4 text-center">
        <p className="text-[11px] text-[#55697A] font-ibm-plex-mono">
          © {new Date().getFullYear()} P2P Platform. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
