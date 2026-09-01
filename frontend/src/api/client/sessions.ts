import type { SessionDetail, SessionItem } from '../../types';
import api from './instance';

export async function listSessions(limit = 50): Promise<SessionItem[]> {
  const { data } = await api.get('/sessions', { params: { limit } });
  return data;
}

export async function getSessionDetail(
  sessionId: string,
): Promise<SessionDetail> {
  const { data } = await api.get(`/sessions/${sessionId}`);
  return data;
}

export async function createSession(
  title = '\u65b0\u5bf9\u8bdd',
): Promise<{ id: string; title: string }> {
  const { data } = await api.post('/sessions', { title });
  return data;
}

export async function renameSession(
  sessionId: string,
  title: string,
): Promise<void> {
  await api.put(`/sessions/${sessionId}`, { title });
}

export async function pinSession(
  sessionId: string,
  isPinned: boolean,
): Promise<void> {
  await api.put(`/sessions/${sessionId}/pin`, { is_pinned: isPinned });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/sessions/${sessionId}`);
}

export interface MemoryItem {
  id: string;
  agent_role: string;
  content_type: string;
  summary: string;
  details: string | null;
  created_at: string | null;
}

export async function listSessionMemories(
  sessionId: string,
): Promise<MemoryItem[]> {
  const { data } = await api.get(`/sessions/${sessionId}/memories`);
  return data;
}

export async function deleteMemory(memoryId: string): Promise<void> {
  await api.delete(`/memories/${memoryId}`);
}

export async function exportSessionMemories(
  sessionId: string,
  format: 'json' | 'md',
): Promise<Blob> {
  const { data } = await api.get(`/sessions/${sessionId}/memories/export`, {
    params: { format },
    responseType: 'blob',
  });
  return data;
}

export async function healthCheck(): Promise<Record<string, unknown>> {
  const { data } = await api.get('/health');
  return data;
}
