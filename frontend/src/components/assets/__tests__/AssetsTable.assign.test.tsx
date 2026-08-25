import type { KnowledgeBase } from '../../../api/client/knowledgeBases';
import type { AssetItem } from '../../../types/assets';
import AssetsTable from '../AssetsTable';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'zh-CN' },
  }),
}));

const KB_A: KnowledgeBase = {
  id: 'kb-1',
  name: '产品文档',
  description: '',
  createdAt: '',
  updatedAt: '',
};
const KB_B: KnowledgeBase = {
  id: 'kb-2',
  name: '技术文档',
  description: '',
  createdAt: '',
  updatedAt: '',
};

const DOC: AssetItem = {
  id: 'a-1',
  name: '报告.pdf',
  assetType: 'document',
  sizeBytes: 1024,
  usageCount: 0,
  indexed: false,
  knowledgeBaseId: null,
};

function renderTable(overrides?: Partial<AssetItem>) {
  const onAssign = vi.fn();
  render(
    <AssetsTable
      assets={[{ ...DOC, ...overrides }]}
      indexing={[]}
      progressMap={{}}
      onPreview={vi.fn()}
      onChunks={vi.fn()}
      onRename={vi.fn()}
      onDelete={vi.fn()}
      onIndex={vi.fn()}
      onRetry={vi.fn()}
      kbs={[KB_A, KB_B]}
      onAssign={onAssign}
    />,
  );
  return onAssign;
}

describe('AssetsTable assign-to-KB row menu', () => {
  it('opens ⋯ menu → assign submenu → dispatches onAssign with kbId', () => {
    const onAssign = renderTable();

    fireEvent.click(screen.getByTestId('more-a-1'));
    fireEvent.click(screen.getByTestId('assign-menu-a-1'));

    // 二级模式列出全部知识库
    expect(screen.getByTestId('assign-kb-kb-1')).toBeInTheDocument();
    expect(screen.getByTestId('assign-kb-kb-2')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('assign-kb-kb-2'));
    expect(onAssign).toHaveBeenCalledWith('a-1', 'kb-2');
  });

  it('marks the current KB as active in the submenu', () => {
    renderTable({ knowledgeBaseId: 'kb-1' });

    fireEvent.click(screen.getByTestId('more-a-1'));
    fireEvent.click(screen.getByTestId('assign-menu-a-1'));

    const active = screen.getByTestId('assign-kb-kb-1');
    expect(active.className).toContain('text-[var(--color-accent)]');
  });
});
