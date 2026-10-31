import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/features/auth/store';
import { reportFrontendError } from '@/shared/lib/telemetry';
import { getResolvedApiUrl } from '@/shared/lib/runtimeConfig';

const resolvedBaseUrl = getResolvedApiUrl();

export const api = axios.create({
  baseURL: resolvedBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor — bearer token biriktiradi
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — 401 da refresh (single-flight)
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (!originalRequest) {
      return Promise.reject(error);
    }

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token) => {
              originalRequest._retry = true;
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(api(originalRequest));
            },
            reject: (err) => reject(err),
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) {
        useAuthStore.getState().logout();
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      try {
        const baseURL = (getResolvedApiUrl() || api.defaults.baseURL || '/api/v1').replace(/\/+$/, '');
        const { data } = await axios.post(
          `${baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const newAccessToken = data.access_token;
        const newRefreshToken = data.refresh_token;
        const onboardingDone = data.onboarding_done;

        useAuthStore.getState().setTokens(newAccessToken, newRefreshToken, onboardingDone);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }

        processQueue(null, newAccessToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        useAuthStore.getState().logout();
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (!originalRequest.url?.includes('/webhooks/')) {
      const status = error.response?.status;
      if ((status && status >= 500) || error.message === 'Network Error') {
        reportFrontendError(
          `API Xatosi (${status || 'Network Error'}): ${originalRequest.method?.toUpperCase()} ${originalRequest.url}`,
          {
            status: status || 0,
            url: originalRequest.url,
            method: originalRequest.method,
            responseData: typeof error.response?.data === 'string' ? error.response.data.slice(0, 300) : error.response?.data,
          },
          'ERROR'
        );
      }
    }

    return Promise.reject(error);
  }
);
export default api;
