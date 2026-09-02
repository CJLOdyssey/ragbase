import { listAssetChunks } from '../../../api/client/assets';
import AssetChunksModal from '../AssetChunksModal';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../api/client/assets', () => ({
  listAssetChunks: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
      language: 'zh-CN',
    },
  }),
}));

const asset = {
  id: 'asset-1',
  name: '产品手册.pdf',
  assetType: 'document',
  sizeBytes: 1024,
  usageCount: 0,
  indexed: true,
  source: 'upload',
  source_ref: null,
};

describe('AssetChunksModal', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  const renderModal = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AssetChunksModal asset={asset} onClose={vi.fn()} />
      </QueryClientProvider>,
    );

  it('renders title with asset name', () => {
    renderModal();
    expect(screen.getByText('assets.chunks.title · 产品手册.pdf')).toBeTruthy();
  });

  it('shows chunks with text and tags', async () => {
    vi.mocked(listAssetChunks).mockResolvedValue([
      { text: '支持三种部署模式', tags: ['spec'], metadata: {} },
      { text: '私有化部署需 4 核 8G', tags: [], metadata: {} },
    ]);
    renderModal();
    await waitFor(() => {
      expect(screen.getByText('支持三种部署模式')).toBeTruthy();
    });
    expect(screen.getByText('私有化部署需 4 核 8G')).toBeTruthy();
    expect(screen.getByText('spec')).toBeTruthy();
  });

  it('shows empty state when no chunks', async () => {
    vi.mocked(listAssetChunks).mockResolvedValue([]);
    renderModal();
    await waitFor(() => {
      expect(screen.getByText('assets.chunks.empty')).toBeTruthy();
    });
  });
});
