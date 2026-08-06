import api from './instance';

export interface KeyItem {
  id: string;
  provider: string;
  usage_type: string;
  label: string;
  key_masked: string;
  base_url: string | null;
  models: string[];
  is_active: boolean;
  is_default: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

export async function listKeys(): Promise<KeyItem[]> {
  const { data } = await api.get('/keys');
  return data;
}

export async function createKey(cfg: {
  provider: string;
  usage_type?: string;
  label: string;
  api_key: string;
  base_url?: string;
  models?: string[];
  is_default?: boolean;
}): Promise<KeyItem> {
  const { data } = await api.post('/keys', cfg);
  return data;
}

export async function updateKey(
  id: string,
  cfg: {
    usage_type?: string;
    label?: string;
    api_key?: string;
    base_url?: string;
    models?: string[];
    is_active?: boolean;
    is_default?: boolean;
  },
): Promise<KeyItem> {
  const { data } = await api.put(`/keys/${id}`, cfg);
  return data;
}

export async function deleteKey(id: string): Promise<void> {
  await api.delete(`/keys/${id}`);
}

export async function testKeyConnection(id: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post(`/keys/${id}/test`);
  return data;
}

export async function getKeyUsage(): Promise<{
  today_requests: number;
  today_tokens: number;
  month_requests: number;
  month_tokens: number;
}> {
  const { data } = await api.get('/keys/usage');
  return data;
}

export async function fetchModelsFromProvider(cfg: {
  api_key: string;
  base_url?: string;
  provider?: string;
}): Promise<{ success: boolean; models: string[]; message?: string }> {
  const { data } = await api.post('/keys/fetch-models', cfg);
  return data;
}
