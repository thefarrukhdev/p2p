import i18n from './i18n';

export function cn(...inputs: Array<string | boolean | undefined | null>) {
  return inputs.filter(Boolean).join(' ');
}

export function getLocaleCode(lang?: string): string {
  const current = lang || i18n.language || 'uz';
  if (current.startsWith('ru')) return 'ru-RU';
  if (current.startsWith('en')) return 'en-US';
  return 'uz-UZ';
}

export function formatDateTime(dateString: string | Date | undefined, locale?: string): string {
  if (!dateString) return '';
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString(getLocaleCode(locale), {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDate(dateString: string | Date | undefined, locale?: string): string {
  if (!dateString) return '';
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  if (isNaN(date.getTime())) return '';
  return date.toLocaleDateString(getLocaleCode(locale), {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatTime(dateString: string | Date | undefined, locale?: string): string {
  if (!dateString) return '';
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  if (isNaN(date.getTime())) return '';
  return date.toLocaleTimeString(getLocaleCode(locale), {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(dateString: string | Date | undefined, locale?: string): string {
  if (!dateString) return '';
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
  if (isNaN(date.getTime())) return '';
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  const lang = (locale || i18n.language || 'uz').slice(0, 2);

  if (lang === 'ru') {
    if (diffSec < 60) return 'Только что';
    if (diffMin < 60) return `${diffMin} мин. назад`;
    if (diffHr < 24) return `${diffHr} ч. назад`;
    if (diffDay < 30) return `${diffDay} дн. назад`;
    return formatDate(date, 'ru');
  }

  if (lang === 'en') {
    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 30) return `${diffDay}d ago`;
    return formatDate(date, 'en');
  }

  if (diffSec < 60) return 'Hozirgincha';
  if (diffMin < 60) return `${diffMin} daqiqa avval`;
  if (diffHr < 24) return `${diffHr} soat avval`;
  if (diffDay < 30) return `${diffDay} kun avval`;
  
  return formatDate(date, 'uz');
}
