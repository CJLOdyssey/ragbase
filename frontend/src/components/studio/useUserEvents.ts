import { useEffect, useRef } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  connectUserEvents,
  disconnectUserEvents,
  type UserEventHandler,
} from '../../api/userEvents';

/**
 * Cross-client realtime sync: connects the authenticated user's events
 * channel and forwards session CRUD events + reconnect to the caller.
 */
export function useUserEvents(
  onEvent: UserEventHandler,
  onReconnect?: () => void,
) {
  const { isAuthenticated } = useAuth();
  const onEventRef = useRef(onEvent);
  const onReconnectRef = useRef(onReconnect);
  useEffect(() => {
    onEventRef.current = onEvent;
    onReconnectRef.current = onReconnect;
  });

  useEffect(() => {
    if (!isAuthenticated) return;
    const handler: UserEventHandler = (e) => onEventRef.current(e);
    const reconnect = () => onReconnectRef.current?.();
    connectUserEvents(handler, reconnect);
    return () => {
      disconnectUserEvents(handler, reconnect);
    };
  }, [isAuthenticated]);
}
