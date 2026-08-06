import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockClient } = vi.hoisted(() => ({
  mockClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockClient }));

import { listVersions, getVersion, createVersion } from '../versions';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listVersions', { tags: ['unit'] }, () => {
  it('calls GET /versions/:type/:id with default params', async () => {
    const mockData = [{ id: '1', resource_type: 'agent', resource_id: 'a1', version_num: 1, snapshot: {}, created_at: '2024-01-01' }];
    mockClient.get.mockResolvedValue({ data: mockData });

    const result = await listVersions('agent', 'a1');

    expect(mockClient.get).toHaveBeenCalledWith('/versions/agent/a1', { params: { limit: 50, offset: 0 } });
    expect(result).toEqual(mockData);
  });

  it('passes custom limit and offset', async () => {
    mockClient.get.mockResolvedValue({ data: [] });

    await listVersions('agent', 'a1', 10, 5);

    expect(mockClient.get).toHaveBeenCalledWith('/versions/agent/a1', { params: { limit: 10, offset: 5 } });
  });
});

describe('getVersion', { tags: ['unit'] }, () => {
  it('calls GET /versions/detail/:id', async () => {
    const mockData = { id: 'v1', resource_type: 'agent', resource_id: 'a1', version_num: 1, snapshot: {}, created_at: '2024-01-01' };
    mockClient.get.mockResolvedValue({ data: mockData });

    const result = await getVersion('v1');

    expect(mockClient.get).toHaveBeenCalledWith('/versions/detail/v1');
    expect(result).toEqual(mockData);
  });
});

describe('createVersion', { tags: ['unit'] }, () => {
  it('calls POST /versions with payload', async () => {
    const snapshot = { name: 'test' };
    const mockData = { id: 'v1', resource_type: 'agent', resource_id: 'a1', version_num: 1, snapshot, created_at: '2024-01-01' };
    mockClient.post.mockResolvedValue({ data: mockData });

    const result = await createVersion('agent', 'a1', snapshot);

    expect(mockClient.post).toHaveBeenCalledWith('/versions', { resource_type: 'agent', resource_id: 'a1', snapshot });
    expect(result).toEqual(mockData);
  });
});
