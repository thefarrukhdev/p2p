import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/features/auth/hooks';
import { useAuthStore } from '@/features/auth/store';
import { LanguageSwitcher } from '@/shared/ui';
import {
  Zap,
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
  Terminal,
  Activity,
  GitCommit,
  Sparkles,
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
    <div className="min-h-screen bg-[#060A10] text-slate-100 flex flex-col justify-between relative select-none font-sans overflow-x-hidden">
      {/* Precision Ambient Cyber Grid & Glow Backdrop */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage:
            'radial-gradient(rgba(24, 214, 199, 0.08) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
          maskImage:
            'radial-gradient(ellipse 90% 80% at 50% 50%, black 40%, transparent 95%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 90% 80% at 50% 50%, black 40%, transparent 95%)',
        }}
      />

      {/* Atmospheric Neon Orbs */}
      <div className="fixed top-[-100px] left-[-100px] w-[500px] h-[500px] bg-[#18D6C7]/12 rounded-full blur-[140px] pointer-events-none z-0" />
      <div className="fixed bottom-[-150px] right-[-100px] w-[600px] h-[600px] bg-[#44EB99]/8 rounded-full blur-[160px] pointer-events-none z-0" />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-[#008BFF]/6 rounded-full blur-[160px] pointer-events-none z-0" />

      {/* Main Split Grid Layout */}
      <div className="w-full max-w-[1440px] mx-auto min-h-screen grid grid-cols-1 lg:grid-cols-12 relative z-10 px-4 sm:px-8 lg:px-12 py-6 sm:py-10 gap-8 lg:gap-16 items-center">
        
        {/* ── LEFT HERO: Interactive Platform Experience (Desktop) ── */}
        <section className="hidden lg:flex lg:col-span-7 flex-col justify-between h-full py-4 space-y-10">
          {/* Brand Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-[#18D6C7] to-[#44EB99] rounded-2xl blur-sm opacity-40 group-hover:opacity-75 transition duration-300" />
                <div className="relative w-11 h-11 rounded-2xl bg-[#0B131E] border border-white/15 flex items-center justify-center shadow-lg">
                  <Zap className="w-5 h-5 text-[#18D6C7]" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-black tracking-tight text-white font-montserrat">
                    P2P Platform
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#18D6C7]/10 text-[#18D6C7] border border-[#18D6C7]/20 font-bold">
                    v2.4
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                  <span className="text-[11px] font-medium text-slate-400">
                    Barcha tizimlar barqaror ishlamoqda
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Hero Pitch */}
          <div className="space-y-5 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#18D6C7]/10 border border-[#18D6C7]/25 text-[#18D6C7] text-xs font-semibold tracking-wide">
              <Sparkles className="w-3.5 h-3.5" />
              <span>PEER-TO-PEER EVALUATION PLATFORM</span>
            </div>

            <h1 className="text-4xl xl:text-5xl font-black text-white leading-[1.15] tracking-tight font-montserrat">
              Kod sifatini charxlang. <br />
              <span className="bg-gradient-to-r from-[#18D6C7] via-[#2EDBB8] to-[#44EB99] bg-clip-text text-transparent">
                Tengdoshlar bilan o'sing.
              </span>
            </h1>

            <p className="text-sm xl:text-base text-slate-400 leading-relaxed max-w-lg">
              Xolis peer-review, avtomatlashtirilgan tekshiruvlar va real loyihalar ustida 
              tengdosh dasturchilar bilan bilim almashinishning ilg'or muhiti.
            </p>
          </div>

          {/* High-Fidelity Interactive Code Review Terminal Card */}
          <div className="relative rounded-2xl bg-[#090F17]/90 border border-white/10 shadow-2xl p-5 backdrop-blur-xl max-w-xl overflow-hidden group">
            {/* Top ambient highlight line */}
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#18D6C7]/50 to-transparent" />

            {/* Terminal Window Header */}
            <div className="flex items-center justify-between pb-3.5 mb-3 border-b border-white/5">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                </div>
                <div className="flex items-center gap-1.5 ml-2 text-xs font-mono text-slate-400">
                  <Terminal className="w-3.5 h-3.5 text-[#18D6C7]" />
                  <span>peer_review_check.ts</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> 100% Passed
                </span>
              </div>
            </div>

            {/* Code Snippet */}
            <div className="font-mono text-xs leading-relaxed space-y-1 text-slate-300">
              <div className="text-slate-500">// 1-bosqich: Peer review tekshiruvi</div>
              <div>
                <span className="text-[#18D6C7]">const</span> session ={' '}
                <span className="text-[#44EB99]">await</span> p2p.
                <span className="text-[#38C9E6]">matchPeerReviewer</span>({'{'}
              </div>
              <div className="pl-4">
                project: <span className="text-amber-300">"P2P-Corpus v2"</span>,
              </div>
              <div className="pl-4">
                criteria: [<span className="text-amber-300">"Architecture"</span>,{' '}
                <span className="text-amber-300">"Clean Code"</span>],
              </div>
              <div>{'}'});</div>
              <div className="pt-1 text-slate-400">
                <span className="text-purple-400">await</span> session.
                <span className="text-emerald-400">approve</span>({'{'}{' '}
                xp: <span className="text-[#44EB99] font-bold">+150</span>, status: <span className="text-emerald-300">"VERIFIED"</span>{' '}
                {'}'});
              </div>
            </div>

            {/* Floating Review Status Pill */}
            <div className="mt-4 pt-3.5 border-t border-white/5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-[#18D6C7] to-[#44EB99] p-[1.5px]">
                  <div className="w-full h-full bg-[#0B131E] rounded-full flex items-center justify-center font-bold text-[10px] text-white">
                    AR
                  </div>
                </div>
                <div>
                  <div className="font-bold text-white text-[11px]">Azizbek R. (Reviewer)</div>
                  <div className="text-[10px] text-slate-400">Peer tekshiruv yakunlandi</div>
                </div>
              </div>
              <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-mono font-bold text-[11px]">
                <GitCommit className="w-3.5 h-3.5" />
                <span>+150 XP</span>
              </div>
            </div>
          </div>

          {/* Bottom Value Props */}
          <div className="grid grid-cols-3 gap-4 max-w-xl pt-2">
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="text-[#18D6C7] font-bold text-base font-montserrat">100% Xolis</div>
              <div className="text-xs text-slate-400 mt-0.5">Tengdosh baholash</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="text-[#44EB99] font-bold text-base font-montserrat">Telegram 2FA</div>
              <div className="text-xs text-slate-400 mt-0.5">Xavfsiz OTP kod</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="text-[#38C9E6] font-bold text-base font-montserrat">Real-vaqt</div>
              <div className="text-xs text-slate-400 mt-0.5">Jonli sessiyalar</div>
            </div>
          </div>
        </section>

        {/* ── RIGHT AUTH: High-End Authentication Card ── */}
        <section className="lg:col-span-5 flex flex-col justify-center items-center w-full my-auto">
          {/* Mobile Top Header */}
          <div className="w-full max-w-[420px] flex items-center justify-between mb-6 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#0B131E] border border-white/15 flex items-center justify-center">
                <Zap className="w-4 h-4 text-[#18D6C7]" />
              </div>
              <span className="font-bold text-white tracking-tight">P2P Platform</span>
            </div>
            <LanguageSwitcher />
          </div>

          {/* Desktop Language Switcher (aligned to card top-right) */}
          <div className="w-full max-w-[440px] hidden lg:flex justify-end mb-4">
            <LanguageSwitcher />
          </div>

          {/* The Glassmorphism Auth Card */}
          <div className="w-full max-w-[440px] relative bg-[#0D1520]/85 backdrop-blur-2xl border border-white/10 rounded-3xl p-7 sm:p-9 shadow-[0_25px_70px_-15px_rgba(0,0,0,0.9),0_0_50px_rgba(24,214,199,0.06)] overflow-hidden">
            {/* Top illuminated cyan laser rim */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-[2px] bg-gradient-to-r from-transparent via-[#18D6C7] to-transparent opacity-90" />

            {/* Header / Brand Mark */}
            <div className="text-center mb-8">
              <div className="relative inline-block mb-4">
                <div className="absolute -inset-1.5 bg-gradient-to-r from-[#18D6C7] to-[#44EB99] rounded-2xl blur-md opacity-30" />
                <div className="relative w-14 h-14 rounded-2xl bg-[#111C28] border border-white/15 flex items-center justify-center shadow-xl">
                  {showOtp ? (
                    <ShieldCheck className="w-7 h-7 text-[#44EB99]" />
                  ) : (
                    <Zap className="w-7 h-7 text-[#18D6C7]" />
                  )}
                </div>
              </div>

              <h2 className="text-2xl font-black text-white tracking-tight font-montserrat">
                {showOtp ? t('login.otpTitle') : t('login.welcome')}
              </h2>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed max-w-xs mx-auto">
                {showOtp ? t('login.otpDescription') : t('login.description')}
              </p>
            </div>

            {!showOtp ? (
              /* Main Credentials Form */
              <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="space-y-4">
                {/* Username Field */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 tracking-wide block">
                    {t('login.loginLabel')}
                  </label>
                  <div
                    className={`relative flex items-center rounded-xl bg-[#070D14] border transition-all duration-200 ${
                      loginErrors.login
                        ? 'border-rose-500/80 ring-2 ring-rose-500/20'
                        : 'border-slate-800 hover:border-slate-700 focus-within:border-[#18D6C7] focus-within:ring-4 focus-within:ring-[#18D6C7]/15'
                    }`}
                  >
                    <div className="pl-3.5 pr-2.5 text-slate-500">
                      <UserIcon className="w-4 h-4 text-[#18D6C7]/70" />
                    </div>
                    <input
                      type="text"
                      disabled={isLoggingIn}
                      autoCapitalize="none"
                      autoComplete="username"
                      spellCheck={false}
                      placeholder={t('login.loginPlaceholder')}
                      {...loginRegister('login')}
                      className="w-full bg-transparent py-3 pr-3 text-sm text-white placeholder-slate-600 focus:outline-none font-sans font-medium"
                    />
                  </div>
                  {loginErrors.login && (
                    <p className="text-[11px] text-rose-400 font-medium pl-1">
                      {loginErrors.login.message}
                    </p>
                  )}
                </div>

                {/* Password Field */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 tracking-wide block">
                    {t('login.passwordLabel')}
                  </label>
                  <div
                    className={`relative flex items-center rounded-xl bg-[#070D14] border transition-all duration-200 ${
                      loginErrors.password
                        ? 'border-rose-500/80 ring-2 ring-rose-500/20'
                        : 'border-slate-800 hover:border-slate-700 focus-within:border-[#18D6C7] focus-within:ring-4 focus-within:ring-[#18D6C7]/15'
                    }`}
                  >
                    <div className="pl-3.5 pr-2.5 text-slate-500">
                      <Lock className="w-4 h-4 text-[#18D6C7]/70" />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      disabled={isLoggingIn}
                      autoComplete="current-password"
                      placeholder={t('login.passwordPlaceholder')}
                      {...loginRegister('password')}
                      className="w-full bg-transparent py-3 pr-3 text-sm text-white placeholder-slate-600 focus:outline-none font-sans font-medium"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="pr-3.5 text-slate-500 hover:text-slate-200 transition-colors cursor-pointer"
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
                    <p className="text-[11px] text-rose-400 font-medium pl-1">
                      {loginErrors.password.message}
                    </p>
                  )}
                </div>

                {/* Action CTA Button */}
                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isLoggingIn}
                    className="w-full h-12 bg-gradient-to-r from-[#18D6C7] via-[#2EDBB8] to-[#44EB99] text-[#04151B] font-bold font-montserrat text-sm tracking-wide rounded-xl shadow-[0_4px_20px_rgba(24,214,199,0.25)] hover:shadow-[0_6px_30px_rgba(24,214,199,0.4)] hover:brightness-105 active:scale-[0.985] transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoggingIn ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-[#04151B]" />
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
                {/* Telegram Helper Banner */}
                <div className="bg-[#070D14] border border-[#229ED9]/30 p-4 rounded-2xl flex flex-col gap-2.5">
                  <div className="flex items-center gap-2 text-[#229ED9]">
                    <Send className="w-4 h-4 shrink-0" />
                    <span className="text-xs font-bold font-montserrat uppercase tracking-wider">
                      {t('login.otpTitle')}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans">
                    {t('login.otpDescription')}
                  </p>
                  {loginData?.bot_url && (
                    <a
                      href={loginData.bot_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-2 py-2.5 px-3 text-xs font-bold text-white bg-[#229ED9] hover:bg-[#1E8DCE] rounded-xl shadow-md shadow-[#229ED9]/20 transition-all mt-1"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{t('login.openBot')}</span>
                    </a>
                  )}
                </div>

                {/* 6-Digit Code Box */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 font-mono tracking-wide block text-center">
                    {t('login.verificationCode')}
                  </label>
                  <div
                    className={`rounded-xl bg-[#070D14] border transition-all duration-200 ${
                      verifyErrors.code
                        ? 'border-rose-500/80 ring-2 ring-rose-500/20'
                        : 'border-slate-800 hover:border-slate-700 focus-within:border-[#18D6C7] focus-within:ring-4 focus-within:ring-[#18D6C7]/15'
                    }`}
                  >
                    <input
                      type="text"
                      maxLength={6}
                      autoFocus
                      disabled={isVerifyingCode}
                      placeholder="000000"
                      {...verifyRegister('code')}
                      className="w-full bg-transparent py-3.5 px-4 text-center text-2xl tracking-[0.45em] text-white placeholder-slate-600 focus:outline-none font-mono font-bold"
                    />
                  </div>
                  {verifyErrors.code && (
                    <p className="text-[11px] text-rose-400 font-medium text-center">
                      {verifyErrors.code.message}
                    </p>
                  )}
                </div>

                {/* Submit & Back Actions */}
                <div className="space-y-2.5 pt-1">
                  <button
                    type="submit"
                    disabled={isVerifyingCode}
                    className="w-full h-12 bg-gradient-to-r from-[#18D6C7] to-[#44EB99] text-[#04151B] font-bold font-montserrat text-sm tracking-wide rounded-xl shadow-[0_4px_20px_rgba(24,214,199,0.25)] hover:shadow-[0_6px_30px_rgba(24,214,199,0.4)] hover:brightness-105 active:scale-[0.985] transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isVerifyingCode ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-[#04151B]" />
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
                    className="w-full py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>{t('login.goBack')}</span>
                  </button>
                </div>
              </form>
            )}

            {/* Security Guarantee Footer */}
            <div className="mt-8 pt-5 border-t border-white/5 flex items-center justify-center gap-2 text-slate-500 text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#18D6C7]" />
              <span>256-bit shifrlangan xavfsiz ulanish • Telegram 2FA</span>
            </div>
          </div>

          {/* Bottom Copyright */}
          <footer className="mt-6 text-center text-[11px] text-slate-500 font-mono">
            © 2026 P2P Platform. Barcha huquqlar himoyalangan.
          </footer>
        </section>
      </div>
    </div>
  );
}
