import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/features/auth/hooks';
import { useAuthStore } from '@/features/auth/store';
import { LanguageSwitcher, DotField } from '@/shared/ui';
import {
  User as UserIcon,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  Send,
  Loader2,
  ShieldCheck,
  CheckCircle2,
  Users,
  CalendarDays,
  Trophy,
  Code2,
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
    <div className="min-h-screen bg-[#1E2A38] text-white flex flex-col justify-between select-none font-sans relative overflow-x-hidden">
      {/* Platform Interactive Background Dot Matrix */}
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

      {/* Top Navigation Bar */}
      <header className="w-full max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 py-3.5 sm:py-5 flex items-center justify-between relative z-40">
        {/* Platform Brand Identity */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-gradient-to-br from-[#38C9E6] to-[#43E8A0] flex items-center justify-center border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:rotate-3 transition-transform cursor-pointer shrink-0">
            <span className="text-black font-extrabold text-[11px] sm:text-xs tracking-tighter font-montserrat">P2P</span>
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-white text-sm sm:text-base leading-tight font-montserrat tracking-tight">
              P2P Platform
            </span>
            <span className="text-[9px] sm:text-[10px] text-[#38C9E6] font-ibm-plex-mono tracking-widest font-black uppercase">
              Peer Learning
            </span>
          </div>
        </div>

        {/* Right Actions: Status Badge & Language */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-[11px] font-bold font-ibm-plex-mono text-[#B0BEC5]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#43E8A0] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#43E8A0]"></span>
            </span>
            <span className="text-white">Tizim faol</span>
            <span className="text-[#38C9E6]">• Peer Hub</span>
          </div>

          <LanguageSwitcher />
        </div>
      </header>

      {/* Main Showcase & Auth Container */}
      <main className="w-full max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 py-4 sm:py-8 lg:py-12 my-auto relative z-10">
        {/* Mobile-Only Hero Banner (Above-the-fold) */}
        <div className="lg:hidden text-center space-y-2 mb-5 sm:mb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold font-montserrat uppercase tracking-wider bg-[#34495E]/80 text-[#38C9E6] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
            <Code2 className="w-3 h-3 text-[#43E8A0]" />
            <span>{t('login.badge')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black font-montserrat tracking-tight text-white leading-tight">
            {t('login.heroTitle')}
          </h1>
          <p className="text-xs sm:text-sm text-[#B0BEC5] leading-relaxed max-w-sm mx-auto font-sans">
            {t('login.heroSubtitle')}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-14 items-center">
          {/* Left Column: Platform Showcase (Visible on Large Screens) */}
          <div className="hidden lg:flex lg:col-span-7 flex-col gap-6 lg:pr-4">
            {/* Tag Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold font-montserrat uppercase tracking-wider bg-[#34495E]/80 text-[#38C9E6] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] w-fit backdrop-blur-md">
              <Code2 className="w-3.5 h-3.5 text-[#43E8A0]" />
              <span>{t('login.badge')}</span>
            </div>

            {/* Headline */}
            <div className="space-y-3">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black font-montserrat tracking-tight text-white leading-[1.15]">
                {t('login.heroTitle')}
              </h1>
              <p className="text-sm sm:text-base text-[#B0BEC5] leading-relaxed max-w-xl font-sans">
                {t('login.heroSubtitle')}
              </p>
            </div>

            {/* 3 Interactive Feature Highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-1">
              {/* Feature 1: Peer Reviews */}
              <div className="bg-[#2A3442]/90 backdrop-blur-md border-2 border-black rounded-2xl p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-2.5 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
                <div className="w-9 h-9 rounded-xl bg-[#38C9E6] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                  <Users className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.p2p.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans line-clamp-3">
                  {t('login.slides.p2p.desc')}
                </p>
              </div>

              {/* Feature 2: Flexible Slots */}
              <div className="bg-[#2A3442]/90 backdrop-blur-md border-2 border-black rounded-2xl p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-2.5 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
                <div className="w-9 h-9 rounded-xl bg-[#43E8A0] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                  <CalendarDays className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.slots.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans line-clamp-3">
                  {t('login.slides.slots.desc')}
                </p>
              </div>

              {/* Feature 3: Skill Radar & XP */}
              <div className="bg-[#2A3442]/90 backdrop-blur-md border-2 border-black rounded-2xl p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-2.5 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
                <div className="w-9 h-9 rounded-xl bg-[#F1A700] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                  <Trophy className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.gamification.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans line-clamp-3">
                  {t('login.slides.gamification.desc')}
                </p>
              </div>
            </div>

            {/* Quick Architecture / Trust Indicators */}
            <div className="flex flex-wrap items-center gap-3 pt-1 text-xs font-bold font-ibm-plex-mono text-[#B0BEC5]">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#43E8A0]" />
                <span>Real-time WebSocket</span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#38C9E6]" />
                <span>Telegram 2FA Himoyasi</span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#F1A700]" />
                <span>Ko'nikmalar Radari</span>
              </span>
            </div>
          </div>

          {/* Right Column: Platform Auth Card */}
          <div className="lg:col-span-5 w-full max-w-md mx-auto">
            <div className="bg-[#2A3442] border-2 border-black rounded-2xl sm:rounded-3xl p-5 sm:p-8 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] sm:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-5 sm:gap-6 relative backdrop-blur-lg">
              {/* Card Header */}
              <div className="flex items-center justify-between border-b-2 border-black pb-3.5 sm:pb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-[#38C9E6] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                    <Lock className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="text-base sm:text-lg font-black font-montserrat text-white uppercase tracking-tight leading-none">
                      {showOtp ? t('login.otpTitle') : t('login.welcome')}
                    </h2>
                  </div>
                </div>
                <span className="text-[10px] font-ibm-plex-mono font-bold px-2 py-0.5 rounded-md bg-[#34495E] text-[#38C9E6] border-2 border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                  PEER AUTH
                </span>
              </div>

              <p className="text-xs text-[#B0BEC5] leading-relaxed -mt-1 sm:-mt-2">
                {showOtp ? t('login.otpDescription') : t('login.description')}
              </p>

              {!showOtp ? (
                /* Regular Credentials Form */
                <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="space-y-4">
                  {/* Login Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs uppercase tracking-wider font-bold font-montserrat text-[#B0BEC5] block">
                      {t('login.loginLabel')}
                    </label>
                    <div
                      className={`flex items-center rounded-xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all ${
                        loginErrors.login
                          ? 'border-[#FF9B9B]'
                          : 'focus-within:border-[#38C9E6] focus-within:shadow-[0_0_0_2px_#38C9E6]'
                      }`}
                    >
                      <div className="pl-3.5 pr-2.5 text-[#B0BEC5]">
                        <UserIcon className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        disabled={isLoggingIn}
                        inputMode="text"
                        autoCapitalize="none"
                        autoCorrect="off"
                        autoComplete="username"
                        spellCheck={false}
                        placeholder={t('login.loginPlaceholder')}
                        {...loginRegister('login')}
                        className="w-full bg-transparent py-3 pr-3 text-base sm:text-sm text-white placeholder-[#78909C] focus:outline-none font-ibm-plex-mono"
                      />
                    </div>
                    {loginErrors.login && (
                      <p className="text-[11px] font-bold text-[#FF9B9B] pl-1 font-ibm-plex-mono">
                        {loginErrors.login.message}
                      </p>
                    )}
                  </div>

                  {/* Password Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs uppercase tracking-wider font-bold font-montserrat text-[#B0BEC5] block">
                      {t('login.passwordLabel')}
                    </label>
                    <div
                      className={`flex items-center rounded-xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all ${
                        loginErrors.password
                          ? 'border-[#FF9B9B]'
                          : 'focus-within:border-[#38C9E6] focus-within:shadow-[0_0_0_2px_#38C9E6]'
                      }`}
                    >
                      <div className="pl-3.5 pr-2.5 text-[#B0BEC5]">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type={showPassword ? 'text' : 'password'}
                        disabled={isLoggingIn}
                        autoComplete="current-password"
                        placeholder={t('login.passwordPlaceholder')}
                        {...loginRegister('password')}
                        className="w-full bg-transparent py-3 pr-2 text-base sm:text-sm text-white placeholder-[#78909C] focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="w-11 h-11 min-w-[44px] min-h-[44px] flex items-center justify-center text-[#B0BEC5] hover:text-white transition-colors cursor-pointer mr-0.5 shrink-0"
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
                      <p className="text-[11px] font-bold text-[#FF9B9B] pl-1 font-ibm-plex-mono">
                        {loginErrors.password.message}
                      </p>
                    )}
                  </div>

                  {/* Submit CTA */}
                  <div className="pt-1.5 sm:pt-2">
                    <button
                      type="submit"
                      disabled={isLoggingIn}
                      className="w-full h-12 min-h-[48px] bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] text-black font-extrabold uppercase tracking-wider font-montserrat text-xs sm:text-sm rounded-xl border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] sm:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[5px_5px_0px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLoggingIn ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-black" />
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
                /* Telegram 2FA Verification Form */
                <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-4">
                  {/* Telegram Info Box */}
                  <div className="bg-[#34495E] border-2 border-black p-3.5 sm:p-4 rounded-2xl shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-3">
                    <div className="flex items-center gap-2 text-[#38C9E6]">
                      <Send className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold uppercase tracking-wider font-montserrat">
                        {t('login.otpTitle')}
                      </span>
                    </div>
                    <p className="text-xs text-[#B0BEC5] leading-relaxed">
                      {t('login.otpDescription')}
                    </p>
                    {loginData?.bot_url && (
                      <a
                        href={loginData.bot_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center gap-2 py-2.5 px-4 min-h-[44px] text-xs font-bold font-montserrat uppercase tracking-wider text-white bg-[#229ED9] hover:bg-[#1E8DCE] rounded-xl border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>{t('login.openBot')}</span>
                      </a>
                    )}
                  </div>

                  {/* 6-Digit Code */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold uppercase tracking-wider font-montserrat text-[#B0BEC5] block text-center">
                      {t('login.verificationCode')}
                    </label>
                    <div
                      className={`rounded-xl bg-[#34495E] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all ${
                        verifyErrors.code
                          ? 'border-[#FF9B9B]'
                          : 'focus-within:border-[#38C9E6] focus-within:shadow-[0_0_0_2px_#38C9E6]'
                      }`}
                    >
                      <input
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        autoComplete="one-time-code"
                        maxLength={6}
                        autoFocus
                        disabled={isVerifyingCode}
                        placeholder="000000"
                        {...verifyRegister('code')}
                        className="w-full bg-transparent py-3 px-4 text-center text-2xl tracking-[0.3em] sm:tracking-[0.4em] text-white placeholder-[#78909C] focus:outline-none font-ibm-plex-mono font-bold"
                      />
                    </div>
                    {verifyErrors.code && (
                      <p className="text-[11px] font-bold text-[#FF9B9B] text-center font-ibm-plex-mono">
                        {verifyErrors.code.message}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="space-y-2.5 pt-1">
                    <button
                      type="submit"
                      disabled={isVerifyingCode}
                      className="w-full h-12 min-h-[48px] bg-gradient-to-r from-[#38C9E6] to-[#43E8A0] text-black font-extrabold uppercase tracking-wider font-montserrat text-xs sm:text-sm rounded-xl border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-[5px_5px_0px_0px_rgba(0,0,0,1)] hover:-translate-x-[1px] hover:-translate-y-[1px] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                    >
                      {isVerifyingCode ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-black" />
                          <span>{t('login.verifyingOtp')}</span>
                        </>
                      ) : (
                        <>
                          <span>{t('login.verifyOtp')}</span>
                          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowOtp(false)}
                      className="w-full py-2.5 min-h-[44px] text-xs font-bold uppercase tracking-wider font-montserrat text-[#B0BEC5] hover:text-white transition-colors flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      <span>{t('login.goBack')}</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Security Badge */}
              <div className="pt-3.5 sm:pt-4 border-t-2 border-black/30 flex items-center justify-center gap-2 text-[11px] sm:text-xs font-ibm-plex-mono text-[#B0BEC5]">
                <ShieldCheck className="w-4 h-4 text-[#43E8A0] shrink-0" />
                <span>256-bit xavfsiz shifrlangan ulanish</span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile-Only Feature Highlights (Below Auth Card) */}
        <div className="lg:hidden flex flex-col gap-4 mt-8 sm:mt-10 pt-6 border-t-2 border-black/30">
          <div className="text-center space-y-1">
            <span className="text-[10px] uppercase font-black tracking-widest text-[#38C9E6] font-ibm-plex-mono">
              Ekotizim
            </span>
            <h2 className="text-base font-extrabold font-montserrat text-white">
              Platforma afzalliklari
            </h2>
          </div>

          <div className="flex flex-col gap-3">
            {/* Mobile Feature 1 */}
            <div className="bg-[#2A3442] border-2 border-black rounded-2xl p-3.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#38C9E6] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                <Users className="w-4 h-4" />
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.p2p.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans">
                  {t('login.slides.p2p.desc')}
                </p>
              </div>
            </div>

            {/* Mobile Feature 2 */}
            <div className="bg-[#2A3442] border-2 border-black rounded-2xl p-3.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#43E8A0] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                <CalendarDays className="w-4 h-4" />
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.slots.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans">
                  {t('login.slides.slots.desc')}
                </p>
              </div>
            </div>

            {/* Mobile Feature 3 */}
            <div className="bg-[#2A3442] border-2 border-black rounded-2xl p-3.5 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#F1A700] border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] shrink-0">
                <Trophy className="w-4 h-4" />
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <h3 className="text-xs font-extrabold font-montserrat text-white uppercase tracking-wider">
                  {t('login.slides.gamification.title')}
                </h3>
                <p className="text-xs text-[#B0BEC5] leading-relaxed font-sans">
                  {t('login.slides.gamification.desc')}
                </p>
              </div>
            </div>
          </div>

          {/* Mobile Trust Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1 text-[11px] font-bold font-ibm-plex-mono text-[#B0BEC5]">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              <CheckCircle2 className="w-3 h-3 text-[#43E8A0]" />
              <span>Real-time WebSocket</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              <CheckCircle2 className="w-3 h-3 text-[#38C9E6]" />
              <span>Telegram 2FA</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-[#2A3442] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
              <CheckCircle2 className="w-3 h-3 text-[#F1A700]" />
              <span>Ko'nikmalar Radari</span>
            </span>
          </div>
        </div>
      </main>

      {/* Platform Footer */}
      <footer className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 text-xs font-ibm-plex-mono text-[#85948F] flex flex-col sm:flex-row items-center justify-between gap-2.5 relative z-10 border-t border-black/20 text-center sm:text-left">
        <div>© 2026 P2P Platform. Barcha huquqlar himoyalangan.</div>
        <div className="flex items-center justify-center gap-3 text-[11px]">
          <span className="text-[#38C9E6] font-bold">v2.4.0</span>
          <span>•</span>
          <span>Peer Learning Ecosystem</span>
        </div>
      </footer>
    </div>
  );
}
