import api from './instance';

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  assetCount?: number;
  createdAt: string;
  updatedAt: string;
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const { data } = await api.get('/knowledge-bases');
  return data;
}

export async function createKnowledgeBase(
  name: string,
  description?: string,
): Promise<KnowledgeBase> {
  const { data } = await api.post('/knowledge-bases', { name, description });
  return data;
}

export async function updateKnowledgeBase(
  id: string,
  name: string,
  description?: string,
): Promise<KnowledgeBase> {
  const { data } = await api.put(`/knowledge-bases/${id}`, {
    name,
    description,
  });
  return data;
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await api.delete(`/knowledge-bases/${id}`);
}

export async function assignAssetToKb(
  assetId: string,
  kbId: string | null,
): Promise<void> {
  await api.post(`/assets/${assetId}/assign-kb`, { knowledge_base_id: kbId });
}
