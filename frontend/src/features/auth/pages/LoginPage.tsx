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
  Key,
  ArrowLeft,
  Send,
  Loader2,
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
    <div className="min-h-screen bg-[#0F172A] text-slate-100 flex flex-col justify-between p-4 sm:p-6 relative select-none font-sans">
      {/* Subtle background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-cyan-500/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Top Bar: Clean header with language toggle */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between py-2 relative z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-emerald-400 p-[1.5px] shadow-sm">
            <div className="w-full h-full bg-[#0F172A] rounded-[10px] flex items-center justify-center">
              <Zap className="w-4 h-4 text-cyan-400" />
            </div>
          </div>
          <span className="text-sm font-bold tracking-tight text-white font-montserrat">
            P2P Platform
          </span>
        </div>

        <LanguageSwitcher />
      </header>

      {/* Center: Minimalist Focused Auth Box */}
      <main className="w-full max-w-[420px] mx-auto my-auto relative z-10 py-8">
        <div className="bg-[#1E293B]/80 backdrop-blur-xl border border-slate-700/60 rounded-2xl p-7 sm:p-8 shadow-2xl shadow-black/40">
          {/* Header */}
          <div className="text-center mb-7">
            <h1 className="text-2xl font-bold text-white tracking-tight font-montserrat">
              {showOtp ? t('login.otpTitle') : t('login.welcome')}
            </h1>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed max-w-xs mx-auto">
              {showOtp ? t('login.otpDescription') : t('login.description')}
            </p>
          </div>

          {!showOtp ? (
            /* Login Form */
            <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="space-y-4">
              {/* Username Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block">
                  {t('login.loginLabel')}
                </label>
                <div
                  className={`relative flex items-center rounded-xl bg-[#0F172A]/80 border transition-all ${
                    loginErrors.login
                      ? 'border-rose-500/80 ring-1 ring-rose-500/30'
                      : 'border-slate-700/80 focus-within:border-cyan-400 focus-within:ring-1 focus-within:ring-cyan-400/30'
                  }`}
                >
                  <div className="pl-3.5 pr-2 text-slate-500">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    disabled={isLoggingIn}
                    autoCapitalize="none"
                    autoComplete="username"
                    placeholder={t('login.loginPlaceholder')}
                    {...loginRegister('login')}
                    className="w-full bg-transparent py-2.5 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-mono"
                  />
                </div>
                {loginErrors.login && (
                  <p className="text-[11px] text-rose-400 pl-1">
                    {loginErrors.login.message}
                  </p>
                )}
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block">
                  {t('login.passwordLabel')}
                </label>
                <div
                  className={`relative flex items-center rounded-xl bg-[#0F172A]/80 border transition-all ${
                    loginErrors.password
                      ? 'border-rose-500/80 ring-1 ring-rose-500/30'
                      : 'border-slate-700/80 focus-within:border-cyan-400 focus-within:ring-1 focus-within:ring-cyan-400/30'
                  }`}
                >
                  <div className="pl-3.5 pr-2 text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    disabled={isLoggingIn}
                    autoComplete="current-password"
                    placeholder={t('login.passwordPlaceholder')}
                    {...loginRegister('password')}
                    className="w-full bg-transparent py-2.5 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="pr-3.5 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
                    tabIndex={-1}
                    aria-label="Toggle password"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {loginErrors.password && (
                  <p className="text-[11px] text-rose-400 pl-1">
                    {loginErrors.password.message}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoggingIn}
                  className="w-full h-11 bg-gradient-to-r from-cyan-400 to-emerald-400 hover:opacity-90 active:scale-[0.99] text-slate-950 font-semibold text-sm rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-cyan-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoggingIn ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{t('login.loggingIn')}</span>
                    </>
                  ) : (
                    <span>{t('login.loginBtn')}</span>
                  )}
                </button>
              </div>
            </form>
          ) : (
            /* OTP Verification Mode */
            <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-4">
              {loginData?.bot_url && (
                <a
                  href={loginData.bot_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 px-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-500/15 transition-all flex items-center justify-center gap-2"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{t('login.openBot')}</span>
                </a>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block text-center">
                  {t('login.verificationCode')}
                </label>
                <div
                  className={`rounded-xl bg-[#0F172A]/80 border transition-all ${
                    verifyErrors.code
                      ? 'border-rose-500/80 ring-1 ring-rose-500/30'
                      : 'border-slate-700/80 focus-within:border-cyan-400 focus-within:ring-1 focus-within:ring-cyan-400/30'
                  }`}
                >
                  <input
                    type="text"
                    maxLength={6}
                    autoFocus
                    disabled={isVerifyingCode}
                    placeholder="000000"
                    {...verifyRegister('code')}
                    className="w-full bg-transparent py-3 px-4 text-center text-xl tracking-[0.4em] text-white placeholder-slate-600 focus:outline-none font-mono font-bold"
                  />
                </div>
                {verifyErrors.code && (
                  <p className="text-[11px] text-rose-400 text-center">
                    {verifyErrors.code.message}
                  </p>
                )}
              </div>

              <div className="space-y-2 pt-2">
                <button
                  type="submit"
                  disabled={isVerifyingCode}
                  className="w-full h-11 bg-gradient-to-r from-cyan-400 to-emerald-400 hover:opacity-90 active:scale-[0.99] text-slate-950 font-semibold text-sm rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-cyan-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isVerifyingCode ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
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
                  className="w-full py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>{t('login.goBack')}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="w-full max-w-5xl mx-auto py-3 text-center relative z-10">
        <p className="text-[11px] text-slate-500 font-mono">
          © {new Date().getFullYear()} P2P Platform. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
