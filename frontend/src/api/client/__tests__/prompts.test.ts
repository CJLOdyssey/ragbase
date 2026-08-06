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
  listPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
  generatePrompt,
  validatePrompt,
} from '../prompts';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listPrompts', { tags: ['unit'] }, () => {
  it('calls GET /prompts', async () => {
    const mockData = [{ id: '1', name: 'prompt1', category: 'general', content: 'Hello', model: null, status: 'active', version: '1.0', created_at: '2024-01-01' }];
    mockApi.get.mockResolvedValue({ data: mockData });

    const result = await listPrompts();

    expect(mockApi.get).toHaveBeenCalledWith('/prompts');
    expect(result).toEqual(mockData);
  });
});

describe('createPrompt', { tags: ['unit'] }, () => {
  it('calls POST /prompts with payload', async () => {
    const payload = { name: 'prompt1', category: 'general', content: 'Hello' };
    const mockData = { id: '1', name: 'prompt1', category: 'general', content: 'Hello', model: null, status: 'active', version: '1.0', created_at: '2024-01-01' };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await createPrompt(payload);

    expect(mockApi.post).toHaveBeenCalledWith('/prompts', payload);
    expect(result).toEqual(mockData);
  });
});

describe('updatePrompt', { tags: ['unit'] }, () => {
  it('calls PUT /prompts/:id with payload', async () => {
    const mockData = { id: '1', name: 'updated', category: 'general', content: 'Hello', model: null, status: 'active', version: '1.0', created_at: '2024-01-01' };
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

describe('generatePrompt', { tags: ['unit'] }, () => {
  it('calls POST /prompts/generate with description and category', async () => {
    const mockData = { id: '1', name: 'gen-prompt', content: 'Generated content', category: 'general', is_valid: true };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await generatePrompt('create a prompt', 'marketing');

    expect(mockApi.post).toHaveBeenCalledWith('/prompts/generate', { description: 'create a prompt', category: 'marketing' });
    expect(result).toEqual(mockData);
  });

  it('defaults category to general', async () => {
    mockApi.post.mockResolvedValue({ data: {} });

    await generatePrompt('description');

    expect(mockApi.post).toHaveBeenCalledWith('/prompts/generate', { description: 'description', category: 'general' });
  });
});

describe('validatePrompt', { tags: ['unit'] }, () => {
  it('calls POST /prompts/validate', async () => {
    const mockData = { is_valid: true, suggestions: [] };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await validatePrompt('content to validate');

    expect(mockApi.post).toHaveBeenCalledWith('/prompts/validate', { content: 'content to validate' });
    expect(result).toEqual(mockData);
  });

  it('returns validation errors', async () => {
    const mockData = { is_valid: false, error_message: 'Invalid syntax', suggestions: ['Fix syntax'] };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await validatePrompt('bad content');

    expect(result).toEqual(mockData);
  });
});
