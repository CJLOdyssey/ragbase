import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TestProviders } from '@/test/setup';
import Modal from '@/components/shared/Modal';

describe('Modal', { tags: ['unit'] }, () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders focusable elements inside modal body', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <input data-testid="input-1" />
          <input data-testid="input-2" />
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByTestId('input-1')).toBeInTheDocument();
    expect(screen.getByTestId('input-2')).toBeInTheDocument();
  });

  it('handles Tab key on non-edge focusable without error', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <input />
          <button>OK</button>
        </Modal>
      </TestProviders>,
    );
    expect(() => {
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: false });
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    }).not.toThrow();
  });

  it('renders with extra className and all ARIA attrs', () => {
    const { container } = render(
      <TestProviders>
        <Modal title="Test" onClose={onClose} className="extra-class">
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    const content = container.querySelector('[role="dialog"]');
    expect(content).toHaveClass('extra-class');
    expect(content).toHaveAttribute('role', 'dialog');
    expect(content).toHaveAttribute('aria-modal', 'true');
  });

  it('renders title and children', () => {
    render(
      <TestProviders>
        <Modal title="Test Modal" onClose={onClose}>
          <p>Modal content</p>
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('renders JSX title', () => {
    render(
      <TestProviders>
        <Modal title={<span>Custom Title</span>} onClose={onClose}>
          <p>Body</p>
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('calls onClose on close button click', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    const closeBtn = screen.getByRole('button');
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on overlay click', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    const overlay = screen.getByText('Test').closest('[role="dialog"]')?.parentElement;
    if (!overlay) throw new Error('dialog overlay not found');
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalled();
  });

  it('does not close on content click', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('Content'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('closes on Escape key', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('renders footer when provided', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose} footer={<button>Save</button>}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByText('Save')).toBeInTheDocument();
  });

  it('does not render footer when not provided', () => {
    const { container } = render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    // Footer div has border-t class; should not exist when footer is not provided
    expect(container.querySelector('[role="dialog"] > [class*="border-t"]')).toBeNull();
  });

  it('applies custom className', () => {
    const { container } = render(
      <TestProviders>
        <Modal title="Test" onClose={onClose} className="custom-class">
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    expect(container.querySelector('.custom-class')).toBeTruthy();
  });

  it('sets correct ARIA attributes', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('wraps Tab from first to last on Shift+Tab', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <input data-testid="input-1" />
          <button data-testid="btn-ok">OK</button>
        </Modal>
      </TestProviders>,
    );
    const dialog = screen.getByRole('dialog');
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'input, button, textarea, select, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first.focus();
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it('wraps Tab from last to first on Tab (no shift)', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose}>
          <input data-testid="input-1" />
          <button data-testid="btn-ok">OK</button>
        </Modal>
      </TestProviders>,
    );
    const dialog = screen.getByRole('dialog');
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'input, button, textarea, select, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    last.focus();
    expect(document.activeElement).toBe(last);
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: false });
    expect(document.activeElement).toBe(first);
  });

  it('sets aria-label when provided', () => {
    render(
      <TestProviders>
        <Modal title="Test" onClose={onClose} ariaLabel="Custom Dialog">
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-label', 'Custom Dialog');
  });

  it('applies width style when provided', () => {
    const { container } = render(
      <TestProviders>
        <Modal title="Test" onClose={onClose} width={480}>
          <p>Content</p>
        </Modal>
      </TestProviders>,
    );
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toHaveStyle({ maxWidth: '480px' });
  });
});
