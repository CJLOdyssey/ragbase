import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ModelOption } from '../types/input';
import * as api from './client';

// ---- Sessions ----

export function useSessions(limit = 50) {
  return useQuery({
    queryKey: ['sessions', limit],
    queryFn: () => api.listSessions(limit),
    staleTime: 30_000,
  });
}

export function useSessionDetail(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSessionDetail(sessionId!),
    enabled: !!sessionId,
    staleTime: 30_000,
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => api.createSession(title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteSession(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}

// ---- Runs ----

export function useRuns(limit = 20) {
  return useQuery({
    queryKey: ['runs', limit],
    queryFn: () => api.listRuns(limit),
    staleTime: 30_000,
  });
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
    staleTime: 30_000,
  });
}

// ---- Available Models (server key vault + backend models API) ----

/**
 * Returns available models from the server-side key vault.
 *
 * The enterprise architecture stores API keys server-side. This hook
 * fetches the key list from GET /api/keys and extracts available models.
 * Also merges GET /api/models (server env var fallback).
 */
export function useAvailableModels(): ModelOption[] {
  const { data: apiModels } = useQuery({
    queryKey: ['models'],
    queryFn: () => api.listModels(),
    staleTime: 0,
    gcTime: 30_000,
  });

  const { data: keys } = useQuery({
    queryKey: ['keys'],
    queryFn: () => api.listKeys(),
    staleTime: 30_000,
    gcTime: 60_000,
  });

  const seen = new Set<string>();
  const models: ModelOption[] = [];

  // 1. Backend /api/models (server env var fallback)
  if (apiModels) {
    for (const m of apiModels) {
      if (seen.has(m.id)) continue;
      seen.add(m.id);
      models.push({ id: m.id, label: m.label, provider: m.provider });
    }
  }

  // 2. Server key vault — active keys with their models
  if (keys) {
    const fromKeys = keys
      .filter((k) => k.is_active)
      .flatMap((k) => k.models.map((modelId) => ({ id: modelId, label: modelId, provider: k.provider })));
    for (const m of fromKeys) {
      if (seen.has(m.id)) continue;
      seen.add(m.id);
      models.push(m);
    }
  }

  return models;
}
