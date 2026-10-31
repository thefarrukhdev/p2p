/**
 * Environment-aware runtime configuration for API, WebSocket, and Telemetry routing.
 * Guarantees staging isolation and safe fail-closed behavior.
 */

export const PRODUCTION_DOMAIN = 'school21-p2p.vercel.app';
export const PRODUCTION_API_URL = 'https://p2p-o1ex.onrender.com/api/v1';

let _envOverride: Record<string, any> | null = null;

export function setRuntimeEnvOverride(override: Record<string, any> | null): void {
  _envOverride = override;
}

function getMetaEnv(): Record<string, any> {
  if (_envOverride) return _envOverride;
  return (typeof import.meta !== 'undefined' && (import.meta as any).env) || {};
}

/**
 * Check if current runtime is running on a staging, preview, or PR deployment.
 */
export function isStagingOrPreview(): boolean {
  const env = getMetaEnv();
  const vercelEnv = env.VITE_VERCEL_ENV || '';
  const isVercelPreviewEnv = vercelEnv === 'preview';
  const isExplicitStaging =
    env.VITE_ENVIRONMENT === 'staging' ||
    env.VITE_ENVIRONMENT === 'preview';

  if (typeof window === 'undefined') {
    return isVercelPreviewEnv || isExplicitStaging;
  }

  const hostname = window.location.hostname;
  const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';
  const isVercelPreviewHost =
    hostname.endsWith('.vercel.app') && hostname !== PRODUCTION_DOMAIN;

  return !isLocal && (isVercelPreviewEnv || isVercelPreviewHost || isExplicitStaging);
}

/**
 * Resolve the API base URL based on environment and hostname.
 * - Staging/Preview MUST provide VITE_API_URL and will NEVER fall back to production.
 * - Staging/Preview MUST fail closed if VITE_API_URL unexpectedly points to production.
 * - Local development uses Vite proxy (/api/v1) or explicit VITE_API_URL.
 * - Production uses explicit VITE_API_URL or defaults to canonical production API URL.
 */
export function getResolvedApiUrl(): string {
  const env = getMetaEnv();
  const envApiUrl = (env.VITE_API_URL || '').trim();

  // In Staging or Preview environments:
  // MUST NEVER silently fall back to production!
  // MUST fail closed if missing or unexpectedly pointing to production!
  if (isStagingOrPreview()) {
    if (!envApiUrl) {
      if (typeof console !== 'undefined') {
        console.error(
          '[CRITICAL] Staging/Preview environment detected, but VITE_API_URL is not configured! ' +
          'Refusing silent fallback to production backend to prevent cross-environment pollution.'
        );
      }
      return '';
    }

    if (envApiUrl.includes('p2p-o1ex.onrender.com')) {
      if (typeof console !== 'undefined') {
        console.error(
          '[CRITICAL] Staging/Preview environment detected, but VITE_API_URL unexpectedly points to ' +
          'PRODUCTION backend (p2p-o1ex)! Refusing connection to prevent production database corruption.'
        );
      }
      return '';
    }

    return envApiUrl.replace(/\/+$/, '');
  }

  // Local development mode
  const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
  const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';
  if (env.DEV || isLocal) {
    if (envApiUrl && !envApiUrl.includes('p2p-r5l6')) {
      return envApiUrl.replace(/\/+$/, '');
    }
    return '/api/v1';
  }

  // Canonical production environment
  const isProdHost = hostname === PRODUCTION_DOMAIN;
  const isProdEnv =
    env.VITE_VERCEL_ENV === 'production' ||
    env.VITE_ENVIRONMENT === 'production';

  if (isProdHost || isProdEnv) {
    if (envApiUrl && !envApiUrl.includes('p2p-r5l6')) {
      return envApiUrl.replace(/\/+$/, '');
    }
    return PRODUCTION_API_URL;
  }

  // If built for production but host/env is unknown and no explicit VITE_API_URL, fail safe
  if (env.PROD) {
    if (envApiUrl && !envApiUrl.includes('p2p-r5l6') && !envApiUrl.includes('p2p-o1ex.onrender.com')) {
      return envApiUrl.replace(/\/+$/, '');
    }
    return '';
  }

  return '/api/v1';
}

/**
 * Resolve real-time WebSocket connection URL from resolved API URL.
 */
export function getResolvedWsUrl(token: string): string {
  if (!token) return '';

  const apiUrl = getResolvedApiUrl();
  if (!apiUrl) {
    return '';
  }

  if (apiUrl.startsWith('http://') || apiUrl.startsWith('https://')) {
    const url = new URL(apiUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws/slots?token=${encodeURIComponent(token)}`;
  }

  // Relative path (local dev with dev proxy)
  if (typeof window !== 'undefined') {
    const loc = window.location;
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${loc.host}/ws/slots?token=${encodeURIComponent(token)}`;
  }

  return '';
}
