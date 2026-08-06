import ConfirmDialog from '@/components/shared/ConfirmDialog';
import { TestProviders } from '@/test/setup';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'confirm.confirm': '确认',
        'confirm.cancel': '取消',
        'confirm.danger': '危险操作',
      };
      return map[key] || key;
    },
  }),
}));

describe('ConfirmDialog', { tags: ['unit'] }, () => {
  it('renders title and message', () => {
    render(
      <TestProviders>
        <ConfirmDialog
          title="Delete Item"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onCancel={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('Delete Item')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
  });

  it('shows danger label when danger', () => {
    render(
      <TestProviders>
        <ConfirmDialog
          title="T"
          message="M"
          danger
          onConfirm={vi.fn()}
          onCancel={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('危险操作')).toBeInTheDocument();
  });

  it('calls onConfirm with custom label', () => {
    const onConfirm = vi.fn();
    render(
      <TestProviders>
        <ConfirmDialog
          title="T"
          message="M"
          confirmLabel="Yes"
          onConfirm={onConfirm}
          onCancel={vi.fn()}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('Yes'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel with custom cancel label', () => {
    const onCancel = vi.fn();
    render(
      <TestProviders>
        <ConfirmDialog
          title="T"
          message="M"
          cancelLabel="No"
          onConfirm={vi.fn()}
          onCancel={onCancel}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('No'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('has no header/footer border lines', () => {
    const { container } = render(
      <TestProviders>
        <ConfirmDialog
          title="T"
          message="M"
          onConfirm={vi.fn()}
          onCancel={vi.fn()}
        />
      </TestProviders>,
    );
    const dialog = container.querySelector('[role="dialog"]')!;
    expect(dialog.querySelector('[class*="border-b"]')).toBeNull();
    expect(dialog.querySelector('[class*="border-t"]')).toBeNull();
  });
});
