import AttachmentPreviewModal from '@/components/input/AttachmentPreviewModal';
import { TestProviders } from '@/test/setup';
import type { AttachedFile } from '@/types/input';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

function makeFile(
  id: string,
  overrides: Partial<AttachedFile> = {},
): AttachedFile {
  return {
    id,
    name: 'notes.md',
    size: 1024,
    type: 'text/markdown',
    status: 'done',
    attachmentId: 'att-1',
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('AttachmentPreviewModal', { tags: ['unit'] }, () => {
  it('renders image for image files', () => {
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    const img = screen.getByRole('img', { name: 'photo.png' });
    expect(img).toHaveAttribute('src', '/api/attachments/att-1');
  });

  it('shows 图片加载失败 and download link when image fails to load', () => {
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    fireEvent.error(screen.getByRole('img', { name: 'photo.png' }));
    expect(screen.getByText('图片加载失败')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'photo.png' })).toBeNull();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/att-1');
    expect(link).toHaveAttribute('download');
  });

  it('fetches and renders text content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () =>
          Promise.resolve({ text: () => Promise.resolve('hello world') }),
      }),
    );
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'notes.md' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    expect(await screen.findByText('hello world')).toBeInTheDocument();
  });

  it('shows loading state while fetching', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'notes.md' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('shows error and download link when fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500 }),
    );
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'notes.md' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    expect(await screen.findByText('预览加载失败')).toBeInTheDocument();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/att-1');
    expect(link).toHaveAttribute('download');
  });

  it('truncates text longer than 64KB', async () => {
    const big = 'y'.repeat(70 * 1024);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve({ text: () => Promise.resolve(big) }),
      }),
    );
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'notes.md' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    const pre = await waitFor(() => {
      const el = document.body.querySelector('pre');
      expect(el).not.toBeNull();
      return el;
    });
    expect(pre.textContent).toContain('…');
    expect(pre.textContent!.length).toBeLessThan(70 * 1024);
    expect(pre.textContent!.endsWith('…(内容过长，已截断)')).toBe(true);
  });

  it('shows download button for unsupported type', () => {
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', {
            name: 'archive.zip',
            type: 'application/zip',
          })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('暂不支持预览该类型')).toBeInTheDocument();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/att-1');
    expect(link).toHaveAttribute('download');
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={onClose}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape', () => {
    const onClose = vi.fn();
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={onClose}
        />
      </TestProviders>,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
