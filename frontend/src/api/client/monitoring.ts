import type { MonitoringSummary } from '../../types/monitoring';
import api from './instance';

export async function fetchMonitoringSummary(
  windowHours = 24,
): Promise<MonitoringSummary> {
  const { data } = await api.get('/monitoring/summary', {
    params: { window_hours: windowHours },
  });
  return data;
}
