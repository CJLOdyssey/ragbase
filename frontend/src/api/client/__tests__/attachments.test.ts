import {
  deleteAttachment,
  uploadAttachment,
  uploadAttachments,
} from '../attachments';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockApi } = vi.hoisted(() => ({
  mockApi: { post: vi.fn(), delete: vi.fn() },
}));

vi.mock('../instance', () => ({ default: mockApi }));

beforeEach(() => {
  vi.resetAllMocks();
});

describe('uploadAttachment', { tags: ['unit'] }, () => {
  it('POSTs multipart form with file and session_id', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 'a1' } });
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });

    const result = await uploadAttachment(file, 's1');

    expect(mockApi.post).toHaveBeenCalledTimes(1);
    const [url, form] = mockApi.post.mock.calls[0] as [string, FormData];
    expect(url).toBe('/attachments');
    expect(form.get('session_id')).toBe('s1');
    expect((form.get('file') as File).name).toBe('hello.txt');
    expect(result).toEqual({ id: 'a1' });
  });

  it('omits session_id when not provided (pre-session upload)', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 'a2' } });
    const file = new File(['x'], 'x.txt', { type: 'text/plain' });

    await uploadAttachment(file, undefined, undefined);

    const form = mockApi.post.mock.calls[0][1] as FormData;
    expect(form.get('session_id')).toBeNull();
  });

  it('reports upload progress', async () => {
    mockApi.post.mockImplementation(
      async (
        _url: string,
        _form: FormData,
        config: {
          onUploadProgress?: (e: { loaded: number; total: number }) => void;
        },
      ) => {
        config.onUploadProgress?.({ loaded: 50, total: 100 });
        return { data: { id: 'a3' } };
      },
    );
    const file = new File(['x'], 'x.txt', { type: 'text/plain' });
    const onProgress = vi.fn();

    await uploadAttachment(file, 's1', undefined, onProgress);

    expect(onProgress).toHaveBeenCalledWith(50);
  });
});

describe('uploadAttachments', { tags: ['unit'] }, () => {
  it('uploads each file separately and returns all ids', async () => {
    mockApi.post.mockResolvedValueOnce({ data: { id: 'a1' } });
    mockApi.post.mockResolvedValueOnce({ data: { id: 'a2' } });

    const result = await uploadAttachments(
      [
        new File(['one'], 'one.txt', { type: 'text/plain' }),
        new File(['two'], 'two.txt', { type: 'text/plain' }),
      ],
      's1',
    );

    expect(mockApi.post).toHaveBeenCalledTimes(2);
    expect(result.map((a) => a.id)).toEqual(['a1', 'a2']);
  });
});

describe('deleteAttachment', { tags: ['unit'] }, () => {
  it('DELETEs the attachment', async () => {
    mockApi.delete.mockResolvedValue({ data: { success: true } });
    await deleteAttachment('att-1');
    expect(mockApi.delete).toHaveBeenCalledWith('/attachments/att-1');
  });
});
