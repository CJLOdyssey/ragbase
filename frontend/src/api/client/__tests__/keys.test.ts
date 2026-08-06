import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockApi }));

import {
  listKeys,
  createKey,
  updateKey,
  deleteKey,
  testKeyConnection,
  getKeyUsage,
  fetchModelsFromProvider,
} from '../keys';

beforeEach(() => {
  vi.resetAllMocks();
});

const mockKeyItem = {
  id: '1', provider: 'openai', usage_type: 'chat', label: 'My Key',
  key_masked: 'sk-***', base_url: null, models: ['gpt-4'], is_active: true,
  is_default: false, last_used_at: null, created_at: '2024-01-01',
};

describe('listKeys', { tags: ['unit'] }, () => {
  it('calls GET /keys', async () => {
    mockApi.get.mockResolvedValue({ data: [mockKeyItem] });

    const result = await listKeys();

    expect(mockApi.get).toHaveBeenCalledWith('/keys');
    expect(result).toEqual([mockKeyItem]);
  });
});

describe('createKey', { tags: ['unit'] }, () => {
  it('calls POST /keys with config', async () => {
    const cfg = { provider: 'openai', label: 'My Key', api_key: 'sk-xxx' };
    mockApi.post.mockResolvedValue({ data: mockKeyItem });

    const result = await createKey(cfg);

    expect(mockApi.post).toHaveBeenCalledWith('/keys', cfg);
    expect(result).toEqual(mockKeyItem);
  });
});

describe('updateKey', { tags: ['unit'] }, () => {
  it('calls PUT /keys/:id with config', async () => {
    const cfg = { label: 'Updated' };
    mockApi.put.mockResolvedValue({ data: { ...mockKeyItem, label: 'Updated' } });

    const result = await updateKey('1', cfg);

    expect(mockApi.put).toHaveBeenCalledWith('/keys/1', cfg);
    expect(result.label).toBe('Updated');
  });
});

describe('deleteKey', { tags: ['unit'] }, () => {
  it('calls DELETE /keys/:id', async () => {
    mockApi.delete.mockResolvedValue({});

    await deleteKey('1');

    expect(mockApi.delete).toHaveBeenCalledWith('/keys/1');
  });
});

describe('testKeyConnection', { tags: ['unit'] }, () => {
  it('calls POST /keys/:id/test', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true, message: 'OK' } });

    const result = await testKeyConnection('1');

    expect(mockApi.post).toHaveBeenCalledWith('/keys/1/test');
    expect(result).toEqual({ success: true, message: 'OK' });
  });
});

describe('getKeyUsage', { tags: ['unit'] }, () => {
  it('calls GET /keys/usage', async () => {
    const usage = { today_requests: 10, today_tokens: 500, month_requests: 100, month_tokens: 5000 };
    mockApi.get.mockResolvedValue({ data: usage });

    const result = await getKeyUsage();

    expect(mockApi.get).toHaveBeenCalledWith('/keys/usage');
    expect(result).toEqual(usage);
  });
});

describe('fetchModelsFromProvider', { tags: ['unit'] }, () => {
  it('calls POST /keys/fetch-models', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true, models: ['gpt-4', 'gpt-3.5'] } });

    const result = await fetchModelsFromProvider({ api_key: 'sk-xxx' });

    expect(mockApi.post).toHaveBeenCalledWith('/keys/fetch-models', { api_key: 'sk-xxx' });
    expect(result).toEqual({ success: true, models: ['gpt-4', 'gpt-3.5'] });
  });

  it('passes all config fields', async () => {
    mockApi.post.mockResolvedValue({ data: { success: true, models: [] } });

    await fetchModelsFromProvider({ api_key: 'sk-xxx', base_url: 'https://api.example.com', provider: 'openai' });

    expect(mockApi.post).toHaveBeenCalledWith('/keys/fetch-models', {
      api_key: 'sk-xxx',
      base_url: 'https://api.example.com',
      provider: 'openai',
    });
  });
});
