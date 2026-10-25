import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/features/auth/hooks';
import { useAuthStore } from '@/features/auth/store';
import { LanguageSwitcher } from '@/shared/ui';
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
    <div className="min-h-screen bg-[#0D1117] text-slate-100 flex flex-col justify-between select-none font-sans">
      {/* Clean Top Navigation Bar */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#161B22] border border-slate-700/80 flex items-center justify-center shadow-sm">
            <span className="font-mono font-bold text-sm text-[#00BFA5]">P2P</span>
          </div>
          <span className="font-semibold text-white tracking-tight text-base font-montserrat">
            P2P Platform
          </span>
        </div>

        <LanguageSwitcher />
      </header>

      {/* Main Centered Content */}
      <main className="w-full max-w-[400px] mx-auto px-4 my-auto py-8">
        {/* Clean Auth Card */}
        <div className="bg-[#161B22] border border-slate-700/60 rounded-2xl p-7 sm:p-8 shadow-xl shadow-black/30">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white tracking-tight">
              {showOtp ? t('login.otpTitle') : t('login.welcome')}
            </h1>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              {showOtp ? t('login.otpDescription') : t('login.description')}
            </p>
          </div>

          {!showOtp ? (
            /* Regular Credentials Form */
            <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="space-y-4">
              {/* Login Field */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block">
                  {t('login.loginLabel')}
                </label>
                <div
                  className={`flex items-center rounded-xl bg-[#0D1117] border transition-colors ${
                    loginErrors.login
                      ? 'border-rose-500'
                      : 'border-slate-700 hover:border-slate-600 focus-within:border-[#00BFA5]'
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
                    spellCheck={false}
                    placeholder={t('login.loginPlaceholder')}
                    {...loginRegister('login')}
                    className="w-full bg-transparent py-2.5 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
                  />
                </div>
                {loginErrors.login && (
                  <p className="text-[11px] text-rose-400 pl-0.5">
                    {loginErrors.login.message}
                  </p>
                )}
              </div>

              {/* Password Field */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block">
                  {t('login.passwordLabel')}
                </label>
                <div
                  className={`flex items-center rounded-xl bg-[#0D1117] border transition-colors ${
                    loginErrors.password
                      ? 'border-rose-500'
                      : 'border-slate-700 hover:border-slate-600 focus-within:border-[#00BFA5]'
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
                    className="w-full bg-transparent py-2.5 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="pr-3 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
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
                  <p className="text-[11px] text-rose-400 pl-0.5">
                    {loginErrors.password.message}
                  </p>
                )}
              </div>

              {/* Submit CTA */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoggingIn}
                  className="w-full h-11 bg-[#00BFA5] hover:bg-[#00A892] active:bg-[#008E7B] text-slate-950 font-semibold text-sm rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {isLoggingIn ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                      <span>{t('login.loggingIn')}</span>
                    </>
                  ) : (
                    <>
                      <span>{t('login.loginBtn')}</span>
                      <ArrowRight className="w-4 h-4 stroke-[2.2]" />
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            /* Telegram 2FA Verification Form */
            <form onSubmit={handleVerifySubmit(onVerifySubmit)} className="space-y-4">
              {/* Telegram Info Box */}
              <div className="bg-[#0D1117] border border-sky-500/30 p-4 rounded-xl flex flex-col gap-2.5">
                <div className="flex items-center gap-2 text-sky-400">
                  <Send className="w-4 h-4 shrink-0" />
                  <span className="text-xs font-semibold uppercase tracking-wider">
                    {t('login.otpTitle')}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {t('login.otpDescription')}
                </p>
                {loginData?.bot_url && (
                  <a
                    href={loginData.bot_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold text-white bg-[#229ED9] hover:bg-[#1E8DCE] rounded-lg transition-colors mt-0.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{t('login.openBot')}</span>
                  </a>
                )}
              </div>

              {/* 6-Digit Code */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 block text-center">
                  {t('login.verificationCode')}
                </label>
                <div
                  className={`rounded-xl bg-[#0D1117] border transition-colors ${
                    verifyErrors.code
                      ? 'border-rose-500'
                      : 'border-slate-700 hover:border-slate-600 focus-within:border-[#00BFA5]'
                  }`}
                >
                  <input
                    type="text"
                    maxLength={6}
                    autoFocus
                    disabled={isVerifyingCode}
                    placeholder="000000"
                    {...verifyRegister('code')}
                    className="w-full bg-transparent py-3 px-4 text-center text-xl tracking-[0.4em] text-white placeholder-slate-600 focus:outline-none font-mono font-semibold"
                  />
                </div>
                {verifyErrors.code && (
                  <p className="text-[11px] text-rose-400 text-center">
                    {verifyErrors.code.message}
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="space-y-2 pt-1">
                <button
                  type="submit"
                  disabled={isVerifyingCode}
                  className="w-full h-11 bg-[#00BFA5] hover:bg-[#00A892] active:bg-[#008E7B] text-slate-950 font-semibold text-sm rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isVerifyingCode ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                      <span>{t('login.verifyingOtp')}</span>
                    </>
                  ) : (
                    <>
                      <span>{t('login.verifyOtp')}</span>
                      <ArrowRight className="w-4 h-4 stroke-[2.2]" />
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setShowOtp(false)}
                  className="w-full py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>{t('login.goBack')}</span>
                </button>
              </div>
            </form>
          )}

          {/* Clean Security Badge */}
          <div className="mt-6 pt-4 border-t border-slate-700/50 flex items-center justify-center gap-1.5 text-slate-500 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            <span>Xavfsiz ulanish (256-bit SSL)</span>
          </div>
        </div>
      </main>

      {/* Clean Footer */}
      <footer className="w-full max-w-5xl mx-auto px-6 py-6 text-center text-xs text-slate-500">
        © 2026 P2P Platform. Barcha huquqlar himoyalangan.
      </footer>
    </div>
  );
}
