/**
 * Comprehensive Tests for Staging Isolation, Runtime Config, and Telemetry Sanitization.
 */
import assert from 'node:assert';
import test from 'node:test';
import {
  sanitizeTelemetryUrl,
  sanitizeTelemetryValue,
} from '../telemetry';
import {
  PRODUCTION_API_URL,
  PRODUCTION_DOMAIN,
  getResolvedApiUrl,
  getResolvedWsUrl,
  isStagingOrPreview,
  setRuntimeEnvOverride,
} from '../runtimeConfig';

test('sanitizeTelemetryUrl redacts sensitive query parameters', () => {
  const rawUrl = 'https://example.com/api/v1/auth/callback?token=secret_jwt_token_123&user=john&code=auth_code_99';
  const sanitized = sanitizeTelemetryUrl(rawUrl);
  assert.strictEqual(
    sanitized,
    'https://example.com/api/v1/auth/callback?token=[REDACTED]&user=john&code=[REDACTED]'
  );
});

test('sanitizeTelemetryValue redacts Bearer tokens and passwords', () => {
  const rawMsg = 'Failed with authorization Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz and password: "mySuperSecretPassword"';
  const sanitized = sanitizeTelemetryValue(rawMsg);
  assert.ok(typeof sanitized === 'string');
  assert.ok(!sanitized.includes('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'));
  assert.ok(!sanitized.includes('mySuperSecretPassword'));
  assert.ok(sanitized.includes('Bearer [REDACTED]'));
  assert.ok(sanitized.includes('[REDACTED]'));
});

test('sanitizeTelemetryValue redacts nested dictionary sensitive keys', () => {
  const details = {
    url: 'https://example.com/login?token=abc',
    headers: {
      authorization: 'Bearer secret_tok',
      userToken: 'token_val',
      safeHeader: 'application/json',
    },
    password: 'plain_password',
  };

  const sanitized = sanitizeTelemetryValue(details) as Record<string, any>;
  assert.strictEqual(sanitized.password, '[REDACTED]');
  assert.strictEqual(sanitized.headers.authorization, '[REDACTED]');
  assert.strictEqual(sanitized.headers.userToken, '[REDACTED]');
  assert.strictEqual(sanitized.headers.safeHeader, 'application/json');
  assert.ok(!sanitized.url.includes('abc'));
  assert.ok(sanitized.url.includes('[REDACTED]'));
});

test('staging isolation: preview domain without VITE_API_URL fails closed and does not fall back to production', () => {
  const originalWindow = (globalThis as any).window;
  try {
    setRuntimeEnvOverride({});
    (globalThis as any).window = {
      location: {
        hostname: 'p2p-git-fix-render-runtime-repair-thefarrukhdevs-projects.vercel.app',
      },
    };

    assert.strictEqual(isStagingOrPreview(), true);
    // When VITE_API_URL is missing, it must return empty string (fail closed)
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, '');

    // WebSocket URL must also fail closed
    const wsUrl = getResolvedWsUrl('test-token');
    assert.strictEqual(wsUrl, '');
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});

test('staging isolation: preview domain with VITE_API_URL pointing to production fails closed', () => {
  const originalWindow = (globalThis as any).window;
  try {
    setRuntimeEnvOverride({
      VITE_API_URL: 'https://p2p-o1ex.onrender.com/api/v1',
    });
    (globalThis as any).window = {
      location: {
        hostname: 'p2p-staging.vercel.app',
      },
    };

    assert.strictEqual(isStagingOrPreview(), true);
    // Must refuse to connect to production Render from staging preview
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, '');
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});

test('staging isolation: preview domain with valid staging VITE_API_URL resolves staging endpoints', () => {
  const originalWindow = (globalThis as any).window;
  try {
    setRuntimeEnvOverride({
      VITE_API_URL: 'https://p2p-api-staging.onrender.com/api/v1',
    });
    (globalThis as any).window = {
      location: {
        hostname: 'p2p-git-fix-render-runtime-repair-thefarrukhdevs-projects.vercel.app',
      },
    };

    assert.strictEqual(isStagingOrPreview(), true);
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, 'https://p2p-api-staging.onrender.com/api/v1');

    const wsUrl = getResolvedWsUrl('staging_tok');
    assert.strictEqual(
      wsUrl,
      'wss://p2p-api-staging.onrender.com/ws/slots?token=staging_tok'
    );
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});

test('preview detection recognizes VITE_VERCEL_ENV=preview without browser window', () => {
  const originalWindow = (globalThis as any).window;
  try {
    delete (globalThis as any).window;
    setRuntimeEnvOverride({
      VITE_VERCEL_ENV: 'preview',
      VITE_API_URL: 'https://p2p-api-staging.onrender.com/api/v1',
    });

    assert.strictEqual(isStagingOrPreview(), true);
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, 'https://p2p-api-staging.onrender.com/api/v1');
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});

test('production domain detects canonical production target', () => {
  const originalWindow = (globalThis as any).window;
  try {
    setRuntimeEnvOverride({});
    (globalThis as any).window = {
      location: {
        hostname: PRODUCTION_DOMAIN,
      },
    };

    assert.strictEqual(isStagingOrPreview(), false);
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, PRODUCTION_API_URL);

    const wsUrl = getResolvedWsUrl('valid_token_xyz');
    assert.strictEqual(wsUrl, 'wss://p2p-o1ex.onrender.com/ws/slots?token=valid_token_xyz');
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});

test('local development defaults to relative proxy target', () => {
  const originalWindow = (globalThis as any).window;
  try {
    setRuntimeEnvOverride({
      DEV: true,
    });
    (globalThis as any).window = {
      location: {
        hostname: 'localhost',
      },
    };

    assert.strictEqual(isStagingOrPreview(), false);
    const apiUrl = getResolvedApiUrl();
    assert.strictEqual(apiUrl, '/api/v1');

    const wsUrl = getResolvedWsUrl('local_tok');
    assert.ok(wsUrl.includes('/ws/slots?token=local_tok'));
    assert.ok(!wsUrl.includes('p2p-o1ex'));
  } finally {
    (globalThis as any).window = originalWindow;
    setRuntimeEnvOverride(null);
  }
});
