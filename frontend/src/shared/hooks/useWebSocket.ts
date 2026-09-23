import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/store';
import { triggerToast } from '@/shared/stores/toast';

/**
 * Global real-time WebSocket (`/ws/slots`).
 * StrictMode-safe: cleanup handler'larni o'chirib, keraksiz reconnect/xato
 * churn'ining oldini oladi (dev'da ikki marta mount bo'lganda console toza qoladi).
 */
export function useWebSocket() {
  const queryClient = useQueryClient();
  const { accessToken, isAuthenticated } = useAuthStore();
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;

    let cancelled = false;
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const connect = () => {
      if (cancelled) return;
      const apiUrl = import.meta.env.VITE_API_URL || '';
      let wsUrl = '';
      
      if (apiUrl.startsWith('http')) {
        const url = new URL(apiUrl);
        const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${url.host}/ws/slots?token=${accessToken}`;
      } else {
        const loc = window.location;
        const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${loc.host}/ws/slots?token=${accessToken}`;
      }
      
      ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'slot_update') {
            queryClient.invalidateQueries({ queryKey: ['slots'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
          } else if (message.type === 'notification') {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['dashboard'] });
            triggerToast('Yangi bildirishnoma', 'info');
          }
        } catch {
          /* noqonuniy xabar — e'tiborsiz qoldiriladi */
        }
      };

      ws.onclose = (event) => {
        if (cancelled) return;
        // 4401 — autentifikatsiya xatosi
        if (event.code === 4401) {
          triggerToast('Aloqa seansi tugadi, iltimos qayta kiring.', 'error');
          useAuthStore.getState().logout();
          return;
        }
        // Kutilmagan uzilish — 3 soniyadan keyin qayta ulanish
        reconnectTimer = window.setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (ws) {
        // Handler'larni o'chiramiz — cleanup close onclose/onerror'ni trigger qilmasin
        ws.onclose = null;
        ws.onmessage = null;
        ws.onerror = null;
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => {
            try { ws.close(); } catch { /* silent */ }
          };
        } else {
          try { ws.close(); } catch { /* silent */ }
        }
      }
      socketRef.current = null;
    };
  }, [accessToken, isAuthenticated, queryClient]);
}
export default useWebSocket;
