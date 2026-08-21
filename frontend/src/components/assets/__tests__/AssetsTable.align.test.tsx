import { TestProviders } from '../../../test/setup';
import type { AssetItem } from '../../../types/assets';
import AssetsTable from '../AssetsTable';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const mockAssets: AssetItem[] = [
  {
    id: '1',
    name: 'brand.md',
    assetType: 'document',
    sizeBytes: 2048,
    usageCount: 1,
    indexed: false,
  },
];

const handlers = {
  onPreview: vi.fn(),
  onChunks: vi.fn(),
  onRename: vi.fn(),
  onDelete: vi.fn(),
  onIndex: vi.fn(),
  onRetry: vi.fn(),
};

describe('AssetsTable alignment', { tags: ['unit'] }, () => {
  it('table header 操作 aligns center between chunks and more', () => {
    render(
      <TestProviders>
        <AssetsTable
          assets={mockAssets}
          indexing={[]}
          progressMap={{}}
          {...handlers}
        />
      </TestProviders>,
    );
    const header = screen.getByText('操作');
    expect(header.className).toContain('justify-center');
    const rowActions = document.querySelector(
      '[data-testid="asset-item-1"] .justify-center',
    );
    expect(rowActions).toBeInTheDocument();
  });

  it('grid bottom bar actions baseline 27px and ml-auto icon', async () => {
    const { default: AssetsGrid } = await import('../AssetsGrid');
    const { container } = render(
      <TestProviders>
        <AssetsGrid
          assets={mockAssets}
          indexing={[]}
          progressMap={{}}
          {...handlers}
        />
      </TestProviders>,
    );
    const bottomBar = container.querySelector(
      '[data-testid="asset-item-1"] .flex.items-center.gap-1\\.5.pt-3',
    );
    // fallback: query by structure
    const bar = document.querySelector(
      '[data-testid="asset-item-1"] > div:last-child',
    );
    expect(bar?.className).toContain('pt-3');
    expect(bar?.className).toContain('border-t');
    expect(bar?.className).toContain('gap-1.5');
    // check 27px buttons exist
    const buttons = document.querySelectorAll(
      '[data-testid="asset-item-1"] button.w-\\[27px\\]',
    );
    expect(buttons.length).toBeGreaterThan(0);
    // ml-auto icon container
    const mlAuto = document.querySelector(
      '[data-testid="asset-item-1"] .ml-auto',
    );
    expect(mlAuto).toBeInTheDocument();
    // suppress unused
    void bottomBar;
  });
});
