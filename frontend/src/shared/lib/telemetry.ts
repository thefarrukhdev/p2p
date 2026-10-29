/**
 * Frontend Telemetry & Error Reporting to Telegram DevOps Logger
 */

const THROTTLE_MS = 30_000;
const sentErrors = new Map<string, number>();

function canSend(errorKey: string): boolean {
  const now = Date.now();
  const lastSent = sentErrors.get(errorKey);
  if (lastSent && now - lastSent < THROTTLE_MS) {
    return false;
  }
  sentErrors.set(errorKey, now);
  return true;
}

export function reportFrontendError(message: string, details?: Record<string, unknown>, level: 'ERROR' | 'WARN' | 'INFO' = 'ERROR'): void {
  // Faqat brauzer muhitida ishlaydi
  if (typeof window === 'undefined') return;

  const errorKey = `${message}:${details?.url || window.location.pathname}`;
  if (!canSend(errorKey)) {
    return;
  }

  const payload = {
    level,
    source: 'frontend',
    message,
    details: {
      url: window.location.href,
      pathname: window.location.pathname,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      ...details,
    },
  };

  try {
    const endpoint = '/api/v1/webhooks/log';
    const body = JSON.stringify(payload);

    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(endpoint, blob);
    } else {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {
        // Logging fail silent
      });
    }
  } catch {
    // Logging fail silent
  }
}

/**
 * Global xatoliklarni kuzatuvchi avtomatik listenerlarni ishga tushirish
 */
export function initFrontendTelemetry(): void {
  if (typeof window === 'undefined') return;

  // Uncaught JavaScript exceptions
  window.addEventListener('error', (event) => {
    reportFrontendError(
      event.message || 'Noma\'lum JavaScript xatosi',
      {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack?.slice(0, 1000),
      },
      'ERROR'
    );
  });

  // Unhandled Promise Rejections (e.g. async/await failures)
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const msg = reason?.message || String(reason || 'Noma\'lum asinxron xato');
    reportFrontendError(
      `Unhandled Promise Rejection: ${msg}`,
      {
        stack: reason?.stack?.slice(0, 1000),
      },
      'ERROR'
    );
  });
}
