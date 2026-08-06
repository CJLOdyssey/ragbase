import client from './instance';

export interface VersionEntry {
  id: string;
  resource_type: string;
  resource_id: string;
  version_num: number;
  snapshot: Record<string, unknown>;
  created_by?: string;
  created_at: string;
}

export async function listVersions(
  resourceType: string,
  resourceId: string,
  limit = 50,
  offset = 0,
): Promise<VersionEntry[]> {
  const { data } = await client.get(`/versions/${resourceType}/${resourceId}`, {
    params: { limit, offset },
  });
  return data;
}

export async function getVersion(versionId: string): Promise<VersionEntry> {
  const { data } = await client.get(`/versions/detail/${versionId}`);
  return data;
}

export async function createVersion(
  resourceType: string,
  resourceId: string,
  snapshot: Record<string, unknown>,
): Promise<VersionEntry> {
  const { data } = await client.post('/versions', {
    resource_type: resourceType,
    resource_id: resourceId,
    snapshot,
  });
  return data;
}
