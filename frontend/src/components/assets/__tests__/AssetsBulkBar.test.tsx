import type { KnowledgeBase } from '../../../api/client/knowledgeBases';
import AssetsBulkBar from '../AssetsBulkBar';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.count != null ? `${key}:${opts.count}` : key,
    i18n: { language: 'zh-CN' },
  }),
}));

const KBS: KnowledgeBase[] = [
  {
    id: 'kb-1',
    name: '产品文档',
    description: '',
    createdAt: '',
    updatedAt: '',
  },
  {
    id: 'kb-2',
    name: '技术文档',
    description: '',
    createdAt: '',
    updatedAt: '',
  },
];

function renderBar(overrides?: Partial<Parameters<typeof AssetsBulkBar>[0]>) {
  const onAssign = vi.fn();
  const onIndex = vi.fn();
  const onCancel = vi.fn();
  render(
    <AssetsBulkBar
      count={3}
      kbs={KBS}
      assigning={false}
      indexing={false}
      canIndex={true}
      onAssign={onAssign}
      onIndex={onIndex}
      onCancel={onCancel}
      {...overrides}
    />,
  );
  return { onAssign, onIndex, onCancel };
}

describe('AssetsBulkBar', () => {
  it('shows selection count and dispatches assign after picking a KB', () => {
    const { onAssign } = renderBar();

    expect(screen.getByTestId('assets-bulk-bar')).toHaveTextContent(
      'assets.bulk.selected:3',
    );

    fireEvent.click(screen.getByTestId('bulk-assign-trigger'));
    fireEvent.click(screen.getByTestId('bulk-assign-kb-kb-2'));
    expect(onAssign).toHaveBeenCalledWith('kb-2');
  });

  it('disables assign when no KBs exist, shows hint instead', () => {
    renderBar({ kbs: [] });
    const trigger = screen.getByTestId('bulk-assign-trigger');
    expect(trigger).toBeDisabled();
    expect(trigger).toHaveTextContent('assets.bulk.noKbs');
  });

  it('disables index action when canIndex is false', () => {
    const { onIndex } = renderBar({ canIndex: false });
    const btn = screen.getByTestId('bulk-index');
    expect(btn).toBeDisabled();
    fireEvent.click(btn);
    expect(onIndex).not.toHaveBeenCalled();
  });

  it('cancel clears selection via callback', () => {
    const { onCancel } = renderBar();
    fireEvent.click(screen.getByTestId('bulk-cancel'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('disables all actions while a bulk operation is running', () => {
    renderBar({ assigning: true, canIndex: true });
    expect(screen.getByTestId('bulk-assign-trigger')).toBeDisabled();
    expect(screen.getByTestId('bulk-index')).toBeDisabled();
    expect(screen.getByTestId('bulk-cancel')).toBeDisabled();
  });
});
