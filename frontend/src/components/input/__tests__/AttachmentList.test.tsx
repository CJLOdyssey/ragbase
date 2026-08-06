import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TestProviders } from '@/test/setup';
import AttachmentList from '@/components/input/AttachmentList';
import type { AttachedFile } from '@/types/input';

function makeFile(id: string, overrides: Partial<AttachedFile> = {}): AttachedFile {
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
    expect(container.querySelector('.agentstudio-attached-files')).toBeNull();
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
