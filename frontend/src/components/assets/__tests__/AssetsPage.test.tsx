import { TestProviders } from '../../../test/setup';
import type { AssetItem } from '../../../types/assets';
import AssetsPage from '../AssetsPage';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks, kbMocks } = vi.hoisted(() => ({
  mocks: {
    listAssets: vi.fn(),
    uploadAsset: vi.fn(),
    renameAsset: vi.fn(),
    deleteAsset: vi.fn(),
    indexAsset: vi.fn(),
    getIndexProgress: vi
      .fn()
      .mockResolvedValue({ stage: null, percentage: 0, message: '' }),
    retryIndexAsset: vi.fn().mockResolvedValue({ retrying: true }),
    importUrl: vi.fn().mockResolvedValue({
      id: 'a1',
      name: 'x',
      assetType: 'document',
      sizeBytes: 100,
      usageCount: 0,
      indexed: false,
    }),
    listAssetChunks: vi.fn().mockResolvedValue([]),
  },
  kbMocks: {
    listKnowledgeBases: vi.fn().mockResolvedValue([]),
    assignAssetToKb: vi.fn(),
    batchAssignAssetsToKb: vi
      .fn()
      .mockResolvedValue({ assignedCount: 0, skippedCount: 0 }),
  },
}));

vi.mock('../../../api/client/assets', () => mocks);
vi.mock('../../../api/client/knowledgeBases', () => kbMocks);

const DOC: AssetItem = {
  id: 'a1',
  name: 'brand.md',
  assetType: 'document',
  sizeBytes: 2048,
  usageCount: 1,
  indexed: false,
};

const IMG: AssetItem = {
  id: 'a2',
  name: 'cover.png',
  assetType: 'image',
  sizeBytes: 524288,
  usageCount: 0,
  indexed: false,
};

function renderPage() {
  return render(
    <TestProviders>
      <AssetsPage />
    </TestProviders>,
  );
}

function makeFile(name: string, type: string, size = 1024): File {
  return new File([new Uint8Array(size)], name, { type });
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listAssets.mockResolvedValue([]);
  kbMocks.listKnowledgeBases.mockResolvedValue([]);
  mocks.uploadAsset.mockResolvedValue({ ...DOC, name: 'brand.md' });
  mocks.renameAsset.mockResolvedValue(DOC);
  mocks.deleteAsset.mockResolvedValue({ deleted: true });
  mocks.indexAsset.mockResolvedValue({ indexed: true, chunks: 3 });
});

describe('AssetsPage', { tags: ['unit'] }, () => {
  it('renders empty state when no assets', async () => {
    renderPage();
    expect(await screen.findByText('暂无素材')).toBeTruthy();
  });

  it('renders asset list', async () => {
    mocks.listAssets.mockResolvedValue([DOC, IMG]);
    renderPage();
    expect(await screen.findByTestId('asset-item-a1')).toBeTruthy();
    expect(screen.getByTestId('asset-item-a2')).toBeTruthy();
    expect(screen.getByText('brand.md')).toBeTruthy();
  });

  it('rejects unsupported file type before upload', async () => {
    renderPage();
    await screen.findByText('暂无素材');
    const input = screen.getByTestId('asset-file-input');
    fireEvent.change(input, {
      target: { files: [makeFile('x.exe', 'application/x-msdownload')] },
    });
    expect(await screen.findByText('"x.exe" 格式不支持')).toBeTruthy();
    expect(mocks.uploadAsset).not.toHaveBeenCalled();
  });

  it('uploads a valid file and shows success toast', async () => {
    renderPage();
    await screen.findByText('暂无素材');
    const input = screen.getByTestId('asset-file-input');
    const file = makeFile('note.md', 'text/markdown');
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(mocks.uploadAsset).toHaveBeenCalledWith(file));
    expect(await screen.findByText('上传成功')).toBeTruthy();
  });

  it('accepts docx and xlsx like the backend does', async () => {
    renderPage();
    await screen.findByText('暂无素材');
    const input = screen.getByTestId('asset-file-input');
    const docx = makeFile(
      'a.docx',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    );
    fireEvent.change(input, { target: { files: [docx] } });
    await waitFor(() => expect(mocks.uploadAsset).toHaveBeenCalledWith(docx));
    const xlsx = makeFile(
      'b.xlsx',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
    fireEvent.change(input, { target: { files: [xlsx] } });
    await waitFor(() => expect(mocks.uploadAsset).toHaveBeenCalledWith(xlsx));
  });

  it('rejects oversized file', async () => {
    renderPage();
    await screen.findByText('暂无素材');
    const input = screen.getByTestId('asset-file-input');
    fireEvent.change(input, {
      target: {
        files: [makeFile('big.pdf', 'application/pdf', 25 * 1024 * 1024)],
      },
    });
    expect(await screen.findByText('"big.pdf" 超过大小限制')).toBeTruthy();
    expect(mocks.uploadAsset).not.toHaveBeenCalled();
  });

  it('deletes asset after ConfirmDialog confirmation', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('more-a1'));
    fireEvent.click(await screen.findByTestId('delete-a1'));
    expect(
      await screen.findByText(/确定要删除素材 "brand.md" 吗/),
    ).toBeTruthy();
    fireEvent.click(screen.getByText('确定'));
    await waitFor(() => expect(mocks.deleteAsset).toHaveBeenCalledWith('a1'));
    expect(await screen.findByText('删除成功')).toBeTruthy();
  });

  it('renames asset via modal', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('more-a1'));
    fireEvent.click(await screen.findByTestId('rename-a1'));
    const input = await screen.findByTestId('rename-input');
    fireEvent.change(input, { target: { value: 'new-name.md' } });
    fireEvent.click(screen.getByText('确定'));
    await waitFor(() =>
      expect(mocks.renameAsset).toHaveBeenCalledWith('a1', 'new-name.md'),
    );
  });

  it('indexes a document asset', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('index-a1'));
    await waitFor(() => expect(mocks.indexAsset).toHaveBeenCalledWith('a1'));
    expect(await screen.findByText('索引已建立')).toBeTruthy();
  });

  it('polls list until the indexed flag flips, then stops', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByTestId('index-a1'));
      await vi.advanceTimersByTimeAsync(0);
      expect(
        within(screen.getByTestId('asset-item-a1')).getByTestId(
          'status-processing',
        ),
      ).toBeTruthy();

      mocks.listAssets.mockResolvedValue([{ ...DOC, indexed: true }]);
      await vi.advanceTimersByTimeAsync(3000);
      expect(mocks.listAssets.mock.calls.length).toBeGreaterThan(1);

      const callsAfterIndexed = mocks.listAssets.mock.calls.length;
      await vi.advanceTimersByTimeAsync(10000);
      expect(mocks.listAssets.mock.calls.length).toBe(callsAfterIndexed);
    } finally {
      vi.useRealTimers();
    }
  });

  it('hides index button for image assets', async () => {
    mocks.listAssets.mockResolvedValue([IMG]);
    renderPage();
    await screen.findByTestId('asset-item-a2');
    expect(screen.queryByTestId('index-a2')).toBeNull();
  });

  it('shows uploading state while upload is in flight', async () => {
    mocks.uploadAsset.mockReturnValue(new Promise(() => {}));
    renderPage();
    await screen.findByText('暂无素材');
    fireEvent.change(screen.getByTestId('asset-file-input'), {
      target: { files: [makeFile('note.md', 'text/markdown')] },
    });
    expect(await screen.findByText('上传中…')).toBeTruthy();
  });

  it('shows error toast when upload fails', async () => {
    mocks.uploadAsset.mockRejectedValue(new Error('boom'));
    renderPage();
    await screen.findByText('暂无素材');
    fireEvent.change(screen.getByTestId('asset-file-input'), {
      target: { files: [makeFile('note.md', 'text/markdown')] },
    });
    expect(await screen.findByText('上传失败')).toBeTruthy();
  });

  it('shows error toast when indexing fails', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    mocks.indexAsset.mockRejectedValue(new Error('boom'));
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('index-a1'));
    expect(
      await screen.findByText('仅支持为文档类型素材建立索引'),
    ).toBeTruthy();
  });

  it('cancels delete dialog without deleting', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('more-a1'));
    fireEvent.click(await screen.findByTestId('delete-a1'));
    fireEvent.click(screen.getByText('取消'));
    await waitFor(() => expect(mocks.deleteAsset).not.toHaveBeenCalled());
    expect(screen.queryByText('确定')).toBeNull();
  });

  it('does not rename when name is empty', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('more-a1'));
    fireEvent.click(await screen.findByTestId('rename-a1'));
    const input = await screen.findByTestId('rename-input');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByText('确定'));
    await waitFor(() => expect(mocks.renameAsset).not.toHaveBeenCalled());
  });

  it('formats sizes in MB and B units', async () => {
    mocks.listAssets.mockResolvedValue([
      { ...IMG, sizeBytes: 5 * 1024 * 1024 },
      { ...DOC, id: 'a3', name: 'tiny.txt', sizeBytes: 500 },
    ]);
    renderPage();
    await screen.findByTestId('asset-item-a2');
    expect(screen.getAllByText(/5\.0 MB/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/500 B/).length).toBeGreaterThan(0);
  });

  it('shows indexed badge for indexed assets', async () => {
    mocks.listAssets.mockResolvedValue([{ ...DOC, indexed: true }]);
    renderPage();
    const item = await screen.findByTestId('asset-item-a1');
    expect(within(item).getByTestId('status-indexed')).toBeTruthy();
    expect(screen.queryByTestId('index-a1')).toBeNull();
  });

  it('filters by knowledge base: all / unassigned / specific kb', async () => {
    kbMocks.listKnowledgeBases.mockResolvedValue([
      { id: 'kb-1', name: '产品库' },
    ]);
    mocks.listAssets.mockResolvedValue([
      { ...DOC, id: 'a1', name: 'assigned.md', knowledgeBaseId: 'kb-1' },
      { ...DOC, id: 'a3', name: 'loose.txt' },
    ]);
    renderPage();
    expect(await screen.findByTestId('asset-item-a1')).toBeTruthy();
    expect(screen.getByTestId('asset-item-a3')).toBeTruthy();

    // 未分配 → 仅剩无库素材
    fireEvent.change(screen.getByTestId('filter-kb'), {
      target: { value: 'unassigned' },
    });
    await waitFor(() =>
      expect(screen.queryByTestId('asset-item-a1')).toBeNull(),
    );
    expect(screen.getByTestId('asset-item-a3')).toBeTruthy();

    // 具体知识库 → 仅剩该库素材，chip 显示库名
    fireEvent.change(screen.getByTestId('filter-kb'), {
      target: { value: 'kb-1' },
    });
    await waitFor(() =>
      expect(screen.queryByTestId('asset-item-a3')).toBeNull(),
    );
    expect(screen.getByTestId('asset-item-a1')).toBeTruthy();
    expect(screen.getAllByText('产品库').length).toBeGreaterThan(0);

    // 清除筛选 → 恢复全部
    fireEvent.click(screen.getByTestId('clear-kb-filter'));
    await waitFor(() => {
      expect(screen.getByTestId('asset-item-a1')).toBeTruthy();
      expect(screen.getByTestId('asset-item-a3')).toBeTruthy();
    });
  });

  it('shows failed badge for an asset with persisted indexError', async () => {
    mocks.listAssets.mockResolvedValue([
      { ...DOC, indexError: 'startxref not found' },
    ]);
    renderPage();
    const item = await screen.findByTestId('asset-item-a1');
    expect(within(item).getByTestId('status-failed')).toBeTruthy();
  });

  it('banner click enters unassigned filter with chip', async () => {
    mocks.listAssets.mockResolvedValue([
      { ...DOC, id: 'a1', name: 'assigned.md', knowledgeBaseId: 'kb-1' },
      { ...DOC, id: 'a3', name: 'loose.txt' },
    ]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('assets-uncategorized-banner'));
    // 仅保留未分配素材，chip 显示「未分类」
    await waitFor(() =>
      expect(screen.queryByTestId('asset-item-a1')).toBeNull(),
    );
    expect(screen.getByTestId('asset-item-a3')).toBeTruthy();
    expect(screen.getAllByText('未分类').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByTestId('clear-kb-filter'));
    await waitFor(() =>
      expect(screen.getByTestId('asset-item-a1')).toBeTruthy(),
    );
  });
});
