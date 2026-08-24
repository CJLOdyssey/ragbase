import api from './instance';

export interface RetrievalSource {
  assetId: string | null;
  assetName: string | null;
  text: string;
  similarity: number;
}

export interface RetrievalTestResult {
  originalQuery: string;
  query: string;
  hitCount: number;
  embeddingConfigured: boolean;
  sources: RetrievalSource[];
}

export type RetrievalMethod = 'hybrid' | 'semantic' | 'lexical';

export interface RetrievalTestParams {
  query: string;
  topK?: number;
  rerank?: boolean;
  rewrite?: boolean;
  knowledgeBaseId?: string | null;
  retrievalMethod?: RetrievalMethod;
  tags?: string[];
}

export async function testRetrieval(
  params: RetrievalTestParams,
): Promise<RetrievalTestResult> {
  const { data } = await api.post('/rag/test-retrieval', params);
  return data;
}
