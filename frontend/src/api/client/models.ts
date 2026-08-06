import api from './instance';

export interface ModelInfo {
  id: string;
  label: string;
  provider: string;
}

export async function listModels(): Promise<ModelInfo[]> {
  const { data } = await api.get('/models');
  return data;
}
