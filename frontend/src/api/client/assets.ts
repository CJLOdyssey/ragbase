import type { AssetIndexResult, AssetItem } from '../../types/assets';
import api from './instance';

export async function listAssets(params?: unknown): Promise<AssetItem[]> {
  // 兼容 react-query 直接传入 queryFn 场景：仅当显式传入 {sort_by,order} 才透传
  let clean: Record<string, string> | undefined;
  if (
    params &&
    typeof params === 'object' &&
    !Array.isArray(params) &&
    ('sort_by' in (params as Record<string, unknown>) ||
      'order' in (params as Record<string, unknown>))
  ) {
    const p = params as Record<string, unknown>;
    clean = {};
    if (typeof p.sort_by === 'string') clean.sort_by = p.sort_by;
    if (typeof p.order === 'string') clean.order = p.order;
  }
  const { data } = await api.get('/assets', { params: clean });
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
  const { data } = await api.post(
    '/assets/import-url',
    { url, name },
    { timeout: 60000 },
  );
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
  id?: string;
  enabled?: boolean;
  text: string;
  tags: string[];
  metadata: Record<string, unknown>;
}

export async function listAssetChunks(assetId: string): Promise<AssetChunk[]> {
  const { data } = await api.get(`/assets/${assetId}/chunks`);
  return data;
}

export async function addAssetChunk(
  assetId: string,
  text: string,
): Promise<AssetChunk> {
  const { data } = await api.post(`/assets/${assetId}/chunks`, { text });
  return data;
}

export async function updateAssetChunk(
  assetId: string,
  chunkId: string,
  text: string,
): Promise<AssetChunk> {
  const { data } = await api.patch(`/assets/${assetId}/chunks/${chunkId}`, {
    text,
  });
  return data;
}

export async function deleteAssetChunk(
  assetId: string,
  chunkId: string,
): Promise<void> {
  await api.delete(`/assets/${assetId}/chunks/${chunkId}`);
}

export async function toggleAssetChunk(
  assetId: string,
  chunkId: string,
  enabled: boolean,
): Promise<void> {
  await api.post(`/assets/${assetId}/chunks/${chunkId}/toggle`, { enabled });
}

export async function getAssetContent(
  assetId: string,
): Promise<{ content: string; truncated: boolean; assetType: string }> {
  const { data } = await api.get(`/assets/${assetId}/content`);
  return data;
}

export async function touchAsset(assetId: string): Promise<AssetItem> {
  const { data } = await api.post(`/assets/${assetId}/touch`);
  return data;
}

export async function downloadAssetFile(
  assetId: string,
  fileName: string,
): Promise<void> {
  const resp = await api.get(`/assets/${assetId}/file`, {
    responseType: 'blob',
  });
  const blob = resp.data as Blob;
  // 尝试从 Content-Disposition 取文件名，兜底用传入的 fileName
  const disposition: string | undefined = (
    resp.headers as Record<string, string>
  )?.['content-disposition'];
  let outName = fileName;
  if (disposition) {
    const m =
      /filename="([^"]+)"/.exec(disposition) ||
      /filename=([^;]+)/.exec(disposition);
    if (m?.[1]) outName = decodeURIComponent(m[1].replace(/"/g, '').trim());
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = outName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function setAssetTags(
  assetId: string,
  tags: string[],
): Promise<AssetItem> {
  const { data } = await api.put(`/assets/${assetId}/tags`, { tags });
  return data;
}

export interface QAPair {
  question: string;
  answer: string;
}

export async function addQaChunks(
  assetId: string,
  pairs: QAPair[],
): Promise<{ created: number }> {
  const { data } = await api.post(`/assets/${assetId}/chunks/batch-qa`, {
    pairs,
  });
  return data;
}
