import AttachmentList from '@/components/input/AttachmentList';
import { TestProviders } from '@/test/setup';
import type { AttachedFile } from '@/types/input';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

function makeFile(
  id: string,
  overrides: Partial<AttachedFile> = {},
): AttachedFile {
  return {
    id,
    name: 'test.txt',
    size: 1024,
    type: 'text/plain',
    file: new File(['content'], 'test.txt', { type: 'text/plain' }),
    ...overrides,
  };
}

describe('AttachmentList', { tags: ['unit'] }, () => {
  it('renders nothing when files is empty', () => {
    const { container } = render(
      <TestProviders>
        <AttachmentList files={[]} onRemove={vi.fn()} />
      </TestProviders>,
    );
    expect(container.querySelector('.ragbase-attached-files')).toBeNull();
  });

  it('renders file names', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'readme.md', size: 2048 })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('readme.md')).toBeInTheDocument();
  });

  it('renders file sizes', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { size: 500, name: 'small.txt' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('500B')).toBeInTheDocument();
  });

  it('renders KB size', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { size: 2048, name: 'medium.txt' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('2KB')).toBeInTheDocument();
  });

  it('renders MB size', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { size: 5 * 1024 * 1024, name: 'large.bin' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('5.0MB')).toBeInTheDocument();
  });

  it('renders image file icon for png', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'photo.png', type: 'image/png' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('photo.png')).toBeInTheDocument();
  });

  it('renders file text icon for doc', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'document.md' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('document.md')).toBeInTheDocument();
  });

  it('renders generic file icon for unknown type', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'archive.zip' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('archive.zip')).toBeInTheDocument();
  });

  it('calls onRemove when remove button clicked', () => {
    const onRemove = vi.fn();
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'removable.txt' })]}
          onRemove={onRemove}
        />
      </TestProviders>,
    );
    const removeBtn = screen.getByLabelText('Remove removable.txt');
    removeBtn.click();
    expect(onRemove).toHaveBeenCalledWith('f1');
  });

  it('renders multiple files', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[
            makeFile('f1', { name: 'a.txt' }),
            makeFile('f2', { name: 'b.txt' }),
            makeFile('f3', { name: 'c.txt' }),
          ]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('a.txt')).toBeInTheDocument();
    expect(screen.getByText('b.txt')).toBeInTheDocument();
    expect(screen.getByText('c.txt')).toBeInTheDocument();
  });
});

describe('AttachmentList preview & thumbnails', { tags: ['unit'] }, () => {
  const imageFile = () =>
    makeFile('f1', {
      name: 'photo.png',
      type: 'image/png',
      status: 'done',
      attachmentId: 'att-1',
    });

  it('renders thumbnail for uploaded image', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[imageFile()]}
          onRemove={vi.fn()}
          onPreview={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByRole('img')).toHaveAttribute(
      'src',
      '/api/attachments/att-1',
    );
  });

  it('does not render thumbnail while uploading (no attachmentId)', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[
            makeFile('f1', {
              name: 'photo.png',
              type: 'image/png',
              status: 'uploading',
            }),
          ]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('falls back to icon when thumbnail fails to load', () => {
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} />
      </TestProviders>,
    );
    fireEvent.error(screen.getByRole('img'));
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('calls onPreview with the file when name button clicked', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList
          files={[imageFile()]}
          onRemove={vi.fn()}
          onPreview={onPreview}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Preview photo.png' }));
    expect(onPreview).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'f1' }),
    );
  });

  it('does not call onPreview when prop missing', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('photo.png'));
    expect(onPreview).not.toHaveBeenCalled();
  });

  it('remove button click does not trigger preview', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList
          files={[imageFile()]}
          onRemove={vi.fn()}
          onPreview={onPreview}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo.png' }));
    expect(onPreview).not.toHaveBeenCalled();
  });
});
