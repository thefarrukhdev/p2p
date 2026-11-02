/**
 * Frontend Telemetry & Error Reporting to Telegram DevOps Logger
 */
import { useAuthStore } from '@/features/auth/store';
import { getResolvedApiUrl } from '@/shared/lib/runtimeConfig';

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

/**
 * Redact sensitive query parameters, credentials, and tokens from URLs and strings.
 */
export function sanitizeTelemetryUrl(urlStr: string): string {
  if (!urlStr) return '';
  return urlStr.replace(
    /([?&](?:token|access_token|refresh_token|password|secret|key|api_key|auth|code)=)[^&\s]+/gi,
    '$1[REDACTED]'
  );
}

export function sanitizeTelemetryValue(val: unknown): unknown {
  if (typeof val === 'string') {
    let s = sanitizeTelemetryUrl(val);
    s = s.replace(/Bearer\s+[A-Za-z0-9\-._~+/]+=*/gi, 'Bearer [REDACTED]');
    s = s.replace(
      /(["']?(?:password|secret|token|refresh_token|access_token)["']?\s*[:=]\s*["'])[^"']+/gi,
      '$1[REDACTED]'
    );
    return s;
  }
  if (val && typeof val === 'object' && !Array.isArray(val)) {
    const res: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(val as Record<string, unknown>)) {
      if (/password|secret|token|auth|credential/i.test(k)) {
        res[k] = '[REDACTED]';
      } else {
        res[k] = sanitizeTelemetryValue(v);
      }
    }
    return res;
  }
  if (Array.isArray(val)) {
    return val.map(sanitizeTelemetryValue);
  }
  return val;
}

export function reportFrontendError(
  message: string,
  details?: Record<string, unknown>,
  level: 'ERROR' | 'WARN' | 'INFO' = 'ERROR'
): void {
  // Faqat brauzer muhitida ishlaydi
  if (typeof window === 'undefined') return;

  const currentUrl = sanitizeTelemetryUrl(window.location.href);
  const currentPath = sanitizeTelemetryUrl(window.location.pathname);
  const sanitizedMessage = String(sanitizeTelemetryValue(message) || '');

  const errorKey = `${sanitizedMessage}:${details?.url || currentPath}`;
  if (!canSend(errorKey)) {
    return;
  }

  const baseUrl = getResolvedApiUrl();
  if (!baseUrl) {
    // If staging/preview configuration is missing, fail safe without touching production
    return;
  }

  const sanitizedDetails = details
    ? (sanitizeTelemetryValue(details) as Record<string, unknown>)
    : {};

  const payload = {
    level,
    source: 'frontend',
    message: sanitizedMessage.slice(0, 1000),
    details: {
      url: currentUrl,
      pathname: currentPath,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      ...sanitizedDetails,
    },
  };

  try {
    const endpoint = `${baseUrl}/webhooks/log`;
    const body = JSON.stringify(payload);

    // Check auth state for server-verifiable authentication
    let token: string | null = null;
    try {
      token = useAuthStore.getState().accessToken;
    } catch {
      // Auth store may not be initialized yet
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    fetch(endpoint, {
      method: 'POST',
      headers,
      body,
      keepalive: true,
    }).catch(() => {
      // Logging fail silent
    });
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
      event.message || "Noma'lum JavaScript xatosi",
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
    const msg = reason?.message || String(reason || "Noma'lum asinxron xato");
    reportFrontendError(
      `Unhandled Promise Rejection: ${msg}`,
      {
        stack: reason?.stack?.slice(0, 1000),
      },
      'ERROR'
    );
  });
}
