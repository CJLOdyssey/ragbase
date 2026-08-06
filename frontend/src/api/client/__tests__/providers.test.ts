import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listProviders } from '../providers';

const { mockClient } = vi.hoisted(() => ({
  mockClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockClient }));

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listProviders', { tags: ['unit'] }, () => {
  it('calls GET /providers', async () => {
    const mockData = {
      openai: { name: 'openai', base_url: 'https://api.openai.com', capabilities: ['chat'], docs_url: null },
    };
    mockClient.get.mockResolvedValue({ data: mockData });

    const result = await listProviders();

    expect(mockClient.get).toHaveBeenCalledWith('/providers');
    expect(result).toEqual(mockData);
  });
});
