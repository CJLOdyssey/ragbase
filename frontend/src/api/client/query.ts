import api from './instance';

export interface RewriteRequest {
  query: string;
  history?: Array<{ role: string; content: string }>;
  session_id?: string;
}

export interface RewriteResponse {
  rewritten_query: string;
  original_query: string;
}

export async function rewriteQuery(req: RewriteRequest): Promise<RewriteResponse> {
  const { data } = await api.post('/query/rewrite', req);
  return data;
}
