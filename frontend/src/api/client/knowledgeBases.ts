import api from './instance';

export interface KbParserConfig {
  chunk_size: number;
  overlap: number;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  embedModel?: string | null;
  parserConfig?: KbParserConfig | null;
  assetCount?: number;
  createdAt: string;
  updatedAt: string;
}

/** Frontend-facing camelCase form of KbParserConfig. */
export interface ParserConfigForm {
  chunkSize: number;
  overlap: number;
}

function toBackendConfig(c: ParserConfigForm): KbParserConfig {
  return { chunk_size: c.chunkSize, overlap: c.overlap };
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const { data } = await api.get('/knowledge-bases');
  return data;
}

export async function createKnowledgeBase(
  name: string,
  description: string,
  embedModel: string,
  parserConfig?: ParserConfigForm,
): Promise<KnowledgeBase> {
  const { data } = await api.post('/knowledge-bases', {
    name,
    description,
    embedModel,
    ...(parserConfig && { parserConfig: toBackendConfig(parserConfig) }),
  });
  return data;
}

export async function updateKnowledgeBase(
  id: string,
  name: string,
  description: string,
  embedModel?: string | null,
  parserConfig?: ParserConfigForm,
): Promise<KnowledgeBase> {
  const { data } = await api.put(`/knowledge-bases/${id}`, {
    name,
    description,
    ...(embedModel != null && embedModel !== '' ? { embedModel } : {}),
    ...(parserConfig && { parserConfig: toBackendConfig(parserConfig) }),
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

export interface BatchAssignResult {
  assignedCount: number;
  skippedCount: number;
  skippedIds: string[];
}

export async function batchAssignAssetsToKb(
  assetIds: string[],
  kbId: string,
): Promise<BatchAssignResult> {
  const { data } = await api.post('/assets/assign-kb/batch', {
    asset_ids: assetIds,
    knowledge_base_id: kbId,
  });
  return data;
}
