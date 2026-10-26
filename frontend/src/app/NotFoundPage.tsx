import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Home, Compass } from 'lucide-react';
import { Button } from '@/shared/ui';

export default function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#1E2A38] text-white flex flex-col items-center justify-center p-6 text-center select-none relative overflow-hidden font-sans">
      {/* Decorative backdrop elements */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-[#38C9E6]/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-[#43E8A0]/5 rounded-full blur-3xl pointer-events-none" />

      <div className="border-2 border-black bg-[#2A3442] rounded-3xl max-w-lg w-full p-8 sm:p-10 flex flex-col items-center gap-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative z-10">
        <div className="w-20 h-20 rounded-2xl bg-[#34495E] border-2 border-black flex items-center justify-center text-[#38C9E6] shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
          <Compass className="w-10 h-10 animate-pulse" />
        </div>

        <div className="space-y-2">
          <span className="inline-block px-3 py-1 rounded-lg bg-[#1E2A38] border-2 border-black text-[#F1A700] text-xs font-mono font-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
            ERROR 404
          </span>
          <h1 className="text-2xl sm:text-3xl font-black font-montserrat uppercase tracking-tight text-white">
            Sahifa topilmadi
          </h1>
          <p className="text-sm text-[#B0BEC5] leading-relaxed max-w-sm font-sans">
            Siz qidirayotgan manzil mavjud emas, o'chirilgan yoki ko'chirilgan bo'lishi mumkin.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full pt-2">
          <Button
            variant="secondary"
            onClick={() => navigate(-1)}
            className="flex-1 justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Ortga qaytish</span>
          </Button>

          <Link to="/dashboard" className="flex-1">
            <Button
              variant="primary"
              className="w-full justify-center gap-2"
            >
              <Home className="w-4 h-4" />
              <span>{t('navigation.dashboard', 'Dashboard')}</span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
