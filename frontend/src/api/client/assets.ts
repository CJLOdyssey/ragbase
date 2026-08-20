import type { AssetIndexResult, AssetItem } from '../../types/assets';
import api from './instance';

export async function listAssets(): Promise<AssetItem[]> {
  const { data } = await api.get('/assets');
  return data;
}

export async function uploadAsset(
  file: File,
  name?: string,
): Promise<AssetItem> {
  const form = new FormData();
  form.append('file', file);
  if (name) form.append('name', name);
  const { data } = await api.post('/assets', form, {
    headers: { 'Content-Type': undefined },
  });
  return data;
}

export async function renameAsset(
  assetId: string,
  name: string,
): Promise<AssetItem> {
  const { data } = await api.put(`/assets/${assetId}`, undefined, {
    params: { name },
  });
  return data;
}

export async function deleteAsset(
  assetId: string,
): Promise<{ deleted: boolean }> {
  const { data } = await api.delete(`/assets/${assetId}`);
  return data;
}

export async function indexAsset(assetId: string): Promise<AssetIndexResult> {
  const { data } = await api.post(`/assets/${assetId}/index`);
  return data;
}

export async function importUrl(
  url: string,
  name?: string,
): Promise<AssetItem> {
  const { data } = await api.post('/assets/import-url', { url, name });
  return data;
}

export interface IndexProgress {
  stage: string | null;
  percentage: number;
  message: string;
}

export async function getIndexProgress(
  assetId: string,
): Promise<IndexProgress> {
  const { data } = await api.get(`/assets/${assetId}/progress`);
  return data;
}

export async function retryIndexAsset(
  assetId: string,
): Promise<{ retrying: boolean }> {
  const { data } = await api.post(`/assets/${assetId}/retry-index`);
  return data;
}

export interface AssetChunk {
  text: string;
  tags: string[];
  metadata: Record<string, unknown>;
}

export async function listAssetChunks(assetId: string): Promise<AssetChunk[]> {
  const { data } = await api.get(`/assets/${assetId}/chunks`);
  return data;
}
