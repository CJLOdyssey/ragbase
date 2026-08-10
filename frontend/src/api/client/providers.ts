import client from './instance';

type ProviderCapability =
  | 'chat'
  | 'vector'
  | 'tool'
  | 'image'
  | 'rerank'
  | 'speech2text'
  | 'tts'
  | 'moderation';

interface ProviderInfo {
  name: string;
  base_url: string;
  capabilities: ProviderCapability[];
  docs_url: string | null;
}

export type ProvidersMap = Record<string, ProviderInfo>;

export async function listProviders(): Promise<ProvidersMap> {
  const { data } = await client.get('/providers');
  return data;
}
