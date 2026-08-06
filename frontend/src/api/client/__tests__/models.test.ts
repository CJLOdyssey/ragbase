import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listModels } from '../models';

const { mockApi } = vi.hoisted(() => ({
  mockApi: { get: vi.fn() },
}));

vi.mock('../instance', () => ({ default: mockApi }));

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listModels', { tags: ['unit'] }, () => {
  it('calls GET /models and returns data', async () => {
    const models = [{ id: 'gpt-4', label: 'GPT-4', provider: 'openai' }];
    mockApi.get.mockResolvedValue({ data: models });

    const result = await listModels();

    expect(mockApi.get).toHaveBeenCalledWith('/models');
    expect(result).toEqual(models);
  });
});
