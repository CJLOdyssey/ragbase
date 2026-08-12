import ConfirmModal from '../ConfirmModal';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

describe('ConfirmModal', () => {
  it('renders title and message and fires confirm/cancel', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        title="确认删除"
        message="删除后不可恢复"
        onConfirm={onConfirm}
        onCancel={onCancel}
        danger
      />,
    );
    expect(screen.getByText('确认删除')).toBeInTheDocument();
    expect(screen.getByText('删除后不可恢复')).toBeInTheDocument();
    fireEvent.click(screen.getByText('confirm.confirm'));
    expect(onConfirm).toHaveBeenCalled();
    fireEvent.click(screen.getByText('confirm.cancel'));
    expect(onCancel).toHaveBeenCalled();
  });
});
