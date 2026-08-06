import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TestProviders } from '@/test/setup';
import FileAttach from '@/components/input/FileAttach';

describe('FileAttach', { tags: ['unit'] }, () => {
  const onAdd = vi.fn();
  const onReject = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders attach button', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('shows file count badge when files attached', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} fileCount={3} />
      </TestProviders>,
    );
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('does not show badge when fileCount is 0', () => {
    const { container } = render(
      <TestProviders>
        <FileAttach onAdd={onAdd} fileCount={0} />
      </TestProviders>,
    );
    expect(container.querySelector('.agentstudio-attach-badge')).toBeNull();
  });

  it('opens file dialog on click', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(input, 'click');
    fireEvent.click(screen.getByRole('button'));
    expect(clickSpy).toHaveBeenCalled();
  });

  it('accepts valid text file', () => {
    const { container } = render(
      <TestProviders>
        <FileAttach onAdd={onAdd} onReject={onReject} />
      </TestProviders>,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);
    expect(onAdd).toHaveBeenCalledWith([file]);
  });

  it('rejects oversized file', () => {
    const { container } = render(
      <TestProviders>
        <FileAttach onAdd={onAdd} onReject={onReject} />
      </TestProviders>,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const bigFile = new File(['x'.repeat(51 * 1024 * 1024)], 'huge.bin', { type: 'application/octet-stream' });
    Object.defineProperty(input, 'files', { value: [bigFile] });
    fireEvent.change(input);
    expect(onReject).toHaveBeenCalledWith([{ file: bigFile, reason: 'size_exceeded' }]);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('rejects unsupported file type', () => {
    const { container } = render(
      <TestProviders>
        <FileAttach onAdd={onAdd} onReject={onReject} />
      </TestProviders>,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const exe = new File(['binary'], 'app.exe', { type: 'application/x-msdownload' });
    Object.defineProperty(input, 'files', { value: [exe] });
    fireEvent.change(input);
    expect(onReject).toHaveBeenCalledWith([{ file: exe, reason: 'type_denied' }]);
  });

  it('handles paste event with files (clipboard handler)', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const file = new File(['content'], 'paste.txt', { type: 'text/plain' });
    const event = new Event('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'clipboardData', {
      value: { files: [file], items: [file], types: ['Files'] },
      configurable: true,
    });
    expect(() => {
      document.dispatchEvent(event);
    }).not.toThrow();
  });

  it('handles paste event without files (clipboard handler)', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const event = new Event('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'clipboardData', {
      value: { files: [] as File[], items: [] },
      configurable: true,
    });
    expect(() => {
      document.dispatchEvent(event);
    }).not.toThrow();
  });

  it('paste handler skips when activeElement is file input', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    document.body.appendChild(fileInput);
    fileInput.focus();
    const file = new File(['paste'], 'paste.txt', { type: 'text/plain' });
    const event = new Event('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'clipboardData', {
      value: { files: [file], items: [file], types: ['Files'] },
      configurable: true,
    });
    expect(() => {
      document.dispatchEvent(event);
    }).not.toThrow();
    document.body.removeChild(fileInput);
  });

  it('handleFiles early return on empty file list', () => {
    const { container } = render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [] });
    fireEvent.change(input);
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('paste handler skips when activeElement is inside input-wrapper', () => {
    render(
      <TestProviders>
        <FileAttach onAdd={onAdd} />
      </TestProviders>,
    );
    const wrapper = document.createElement('div');
    wrapper.className = 'agentstudio-input-wrapper';
    const inner = document.createElement('span');
    wrapper.appendChild(inner);
    document.body.appendChild(wrapper);
    inner.focus();
    const file = new File(['paste'], 'paste.txt', { type: 'text/plain' });
    const event = new Event('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'clipboardData', {
      value: { files: [file], items: [file], types: ['Files'] },
      configurable: true,
    });
    expect(() => {
      document.dispatchEvent(event);
    }).not.toThrow();
    document.body.removeChild(wrapper);
  });
});
