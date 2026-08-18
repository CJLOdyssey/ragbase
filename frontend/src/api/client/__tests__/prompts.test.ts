import {
  createPrompt,
  deletePrompt,
  listPrompts,
  updatePrompt,
} from '../prompts';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockApi }));

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listPrompts', { tags: ['unit'] }, () => {
  it('calls GET /prompts', async () => {
    const mockData = [
      {
        id: '1',
        name: 'prompt1',
        category: 'general',
        content: 'Hello',
        model: null,
        status: 'active',
        version: '1.0',
        created_at: '2024-01-01',
      },
    ];
    mockApi.get.mockResolvedValue({ data: mockData });

    const result = await listPrompts();

    expect(mockApi.get).toHaveBeenCalledWith('/prompts');
    expect(result).toEqual(mockData);
  });
});

describe('createPrompt', { tags: ['unit'] }, () => {
  it('calls POST /prompts with payload', async () => {
    const payload = { name: 'prompt1', category: 'general', content: 'Hello' };
    const mockData = {
      id: '1',
      name: 'prompt1',
      category: 'general',
      content: 'Hello',
      model: null,
      status: 'active',
      version: '1.0',
      created_at: '2024-01-01',
    };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await createPrompt(payload);

    expect(mockApi.post).toHaveBeenCalledWith('/prompts', payload);
    expect(result).toEqual(mockData);
  });
});

describe('updatePrompt', { tags: ['unit'] }, () => {
  it('calls PUT /prompts/:id with payload', async () => {
    const mockData = {
      id: '1',
      name: 'updated',
      category: 'general',
      content: 'Hello',
      model: null,
      status: 'active',
      version: '1.0',
      created_at: '2024-01-01',
    };
    mockApi.put.mockResolvedValue({ data: mockData });

    const result = await updatePrompt('1', { name: 'updated' });

    expect(mockApi.put).toHaveBeenCalledWith('/prompts/1', { name: 'updated' });
    expect(result).toEqual(mockData);
  });
});

describe('deletePrompt', { tags: ['unit'] }, () => {
  it('calls DELETE /prompts/:id', async () => {
    mockApi.delete.mockResolvedValue({});

    await deletePrompt('1');

    expect(mockApi.delete).toHaveBeenCalledWith('/prompts/1');
  });
});
