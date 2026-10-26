import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface PageHeaderProps {
  /** Sahifa sarlavhasi (Montserrat, black) */
  title: string;
  /** Sarlavha ostidagi qisqa izoh */
  subtitle?: string;
  /** Chapdagi ikonka (lucide-react) */
  icon?: LucideIcon;
  /** Ikonka rangi (Tailwind class), default teal */
  iconClassName?: string;
  /** O'ng tomondagi harakat tugmalari (masalan "Yaratish") */
  actions?: ReactNode;
}

/**
 * Barcha sahifalar uchun YAGONA sarlavha bloki.
 * DESIGN_SPEC: har bir sahifa root `flex flex-col gap-6 animate-fade-in`
 * ichida birinchi element sifatida `<PageHeader />` ishlatishi kerak.
 */
export function PageHeader({
  title,
  subtitle,
  icon: Icon,
  iconClassName = 'text-[#38C9E6]',
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
      <div className="flex flex-col gap-1 sm:gap-1.5 min-w-0 flex-1">
        <h1 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2 font-montserrat tracking-tight leading-tight">
          {Icon && <Icon className={`h-5 w-5 sm:h-6 sm:w-6 shrink-0 ${iconClassName}`} />}
          <span className="truncate">{title}</span>
        </h1>
        {subtitle && (
          <p className="text-xs text-[#B0BEC5] leading-relaxed max-w-2xl">{subtitle}</p>
        )}
      </div>
      {actions && <div className="w-full sm:w-auto flex items-center gap-2 sm:gap-3 shrink-0 flex-wrap">{actions}</div>}
    </div>
  );
}
export default PageHeader;
