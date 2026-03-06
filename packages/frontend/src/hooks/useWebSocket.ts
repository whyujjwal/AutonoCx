import { useEffect, useRef, useCallback, useState } from 'react';
import { WS_BASE_URL } from '@/lib/constants';
import { useAuthStore } from '@/stores/authStore';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  path: string;
  onMessage?: (data: unknown) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxRetries?: number;
}

export function useWebSocket({
  path,
  onMessage,
  onOpen,
  onClose,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
  maxRetries = 5,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const accessToken = useAuthStore((s) => s.accessToken);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = `${WS_BASE_URL}${path}?token=${accessToken ?? ''}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('connected');
      retriesRef.current = 0;
      onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        onMessage?.(data);
      } catch {
        onMessage?.(event.data);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      onClose?.();

      if (autoReconnect && retriesRef.current < maxRetries) {
        retriesRef.current++;
        reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      setStatus('error');
      onError?.(error);
    };

    wsRef.current = ws;
    setStatus('connecting');
  }, [path, accessToken, onMessage, onOpen, onClose, onError, autoReconnect, reconnectInterval, maxRetries]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeoutRef.current);
    retriesRef.current = maxRetries; // prevent reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setStatus('disconnected');
  }, [maxRetries]);

  const sendMessage = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { status, sendMessage, connect, disconnect };
}
