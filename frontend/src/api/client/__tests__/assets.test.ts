import {
  deleteAsset,
  indexAsset,
  listAssets,
  renameAsset,
  uploadAsset,
} from '../assets';
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

describe('listAssets', { tags: ['unit'] }, () => {
  it('calls GET /assets', async () => {
    const mockData = [
      {
        id: 'a1',
        name: 'doc.md',
        asset_type: 'document',
        size_bytes: 1024,
        usage_count: 0,
        indexed: false,
      },
    ];
    mockApi.get.mockResolvedValue({ data: mockData });

    const result = await listAssets();

    expect(mockApi.get).toHaveBeenCalledWith('/assets');
    expect(result).toEqual(mockData);
  });
});

describe('uploadAsset', { tags: ['unit'] }, () => {
  it('calls POST /assets with form data', async () => {
    const file = new File(['x'], 'a.md', { type: 'text/markdown' });
    const mockData = { id: 'a1' };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await uploadAsset(file);

    const [url, form] = mockApi.post.mock.calls[0];
    expect(url).toBe('/assets');
    expect(form).toBeInstanceOf(FormData);
    expect((form as FormData).get('file')).toBe(file);
    expect(result).toEqual(mockData);
  });

  it('appends name when provided', async () => {
    const file = new File(['x'], 'a.md', { type: 'text/markdown' });
    mockApi.post.mockResolvedValue({ data: { id: 'a1' } });

    await uploadAsset(file, 'custom');

    const form = mockApi.post.mock.calls[0][1] as FormData;
    expect(form.get('name')).toBe('custom');
  });
});

describe('renameAsset', { tags: ['unit'] }, () => {
  it('calls PUT /assets/:id with name param', async () => {
    const mockData = { id: 'a1', name: 'new.md' };
    mockApi.put.mockResolvedValue({ data: mockData });

    const result = await renameAsset('a1', 'new.md');

    expect(mockApi.put).toHaveBeenCalledWith('/assets/a1', undefined, {
      params: { name: 'new.md' },
    });
    expect(result).toEqual(mockData);
  });
});

describe('deleteAsset', { tags: ['unit'] }, () => {
  it('calls DELETE /assets/:id', async () => {
    mockApi.delete.mockResolvedValue({ data: { deleted: true } });

    const result = await deleteAsset('a1');

    expect(mockApi.delete).toHaveBeenCalledWith('/assets/a1');
    expect(result).toEqual({ deleted: true });
  });
});

describe('indexAsset', { tags: ['unit'] }, () => {
  it('calls POST /assets/:id/index', async () => {
    const mockData = { indexed: true, chunks: 3 };
    mockApi.post.mockResolvedValue({ data: mockData });

    const result = await indexAsset('a1');

    expect(mockApi.post).toHaveBeenCalledWith('/assets/a1/index');
    expect(result).toEqual(mockData);
  });
});
