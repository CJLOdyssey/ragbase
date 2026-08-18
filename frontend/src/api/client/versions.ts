import api from './instance';

export interface VersionItem {
  id: string;
  version_num: number;
  snapshot: Record<string, unknown>;
  created_by: string | null;
  created_at: string;
}

export async function listVersions(
  resourceType: string,
  resourceId: string,
  limit: number = 50,
): Promise<VersionItem[]> {
  const { data } = await api.get(`/versions/${resourceType}/${resourceId}`, {
    params: { limit },
  });
  return data;
}

export async function getVersionDetail(
  versionId: string,
): Promise<VersionItem> {
  const { data } = await api.get(`/versions/detail/${versionId}`);
  return data;
}
