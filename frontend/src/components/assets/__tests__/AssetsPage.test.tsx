import { TestProviders } from '../../../test/setup';
import type { AssetItem } from '../../../types/assets';
import AssetsPage from '../AssetsPage';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks } = vi.hoisted(() => ({
  mocks: {
    listAssets: vi.fn(),
    uploadAsset: vi.fn(),
    renameAsset: vi.fn(),
    deleteAsset: vi.fn(),
    indexAsset: vi.fn(),
  },
}));

vi.mock('../../../api/client/assets', () => mocks);

const DOC: AssetItem = {
  id: 'a1',
  name: 'brand.md',
  asset_type: 'document',
  size_bytes: 2048,
  usage_count: 1,
  indexed: false,
};

const IMG: AssetItem = {
  id: 'a2',
  name: 'cover.png',
  asset_type: 'image',
  size_bytes: 524288,
  usage_count: 0,
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
  mocks.uploadAsset.mockResolvedValue({ ...DOC, name: 'brand.md' });
  mocks.renameAsset.mockResolvedValue(DOC);
  mocks.deleteAsset.mockResolvedValue({ deleted: true });
  mocks.indexAsset.mockResolvedValue({ indexed: true, chunks: 3 });
});

describe('AssetsPage', { tags: ['unit'] }, () => {
  it('renders empty state when no assets', async () => {
    renderPage();
    expect(await screen.findByText('暂无素材，点击上方按钮上传')).toBeTruthy();
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
    await screen.findByText('暂无素材，点击上方按钮上传');
    const input = screen.getByTestId('asset-file-input');
    fireEvent.change(input, {
      target: { files: [makeFile('x.exe', 'application/x-msdownload')] },
    });
    expect(await screen.findByText('"x.exe" 格式不支持')).toBeTruthy();
    expect(mocks.uploadAsset).not.toHaveBeenCalled();
  });

  it('uploads a valid file and shows success toast', async () => {
    renderPage();
    await screen.findByText('暂无素材，点击上方按钮上传');
    const input = screen.getByTestId('asset-file-input');
    const file = makeFile('note.md', 'text/markdown');
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(mocks.uploadAsset).toHaveBeenCalledWith(file));
    expect(await screen.findByText('上传成功')).toBeTruthy();
  });

  it('rejects oversized file', async () => {
    renderPage();
    await screen.findByText('暂无素材，点击上方按钮上传');
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
    fireEvent.click(screen.getByTestId('delete-a1'));
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
    fireEvent.click(screen.getByTestId('rename-a1'));
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

  it('hides index button for image assets', async () => {
    mocks.listAssets.mockResolvedValue([IMG]);
    renderPage();
    await screen.findByTestId('asset-item-a2');
    expect(screen.queryByTestId('index-a2')).toBeNull();
  });

  it('shows uploading state while upload is in flight', async () => {
    mocks.uploadAsset.mockReturnValue(new Promise(() => {}));
    renderPage();
    await screen.findByText('暂无素材，点击上方按钮上传');
    fireEvent.change(screen.getByTestId('asset-file-input'), {
      target: { files: [makeFile('note.md', 'text/markdown')] },
    });
    expect(await screen.findByText('上传中…')).toBeTruthy();
  });

  it('shows error toast when upload fails', async () => {
    mocks.uploadAsset.mockRejectedValue(new Error('boom'));
    renderPage();
    await screen.findByText('暂无素材，点击上方按钮上传');
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
    fireEvent.click(screen.getByTestId('delete-a1'));
    fireEvent.click(screen.getByText('取消'));
    await waitFor(() => expect(mocks.deleteAsset).not.toHaveBeenCalled());
    expect(screen.queryByText('确定')).toBeNull();
  });

  it('does not rename when name is empty', async () => {
    mocks.listAssets.mockResolvedValue([DOC]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    fireEvent.click(screen.getByTestId('rename-a1'));
    const input = await screen.findByTestId('rename-input');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByText('确定'));
    await waitFor(() => expect(mocks.renameAsset).not.toHaveBeenCalled());
  });

  it('formats sizes in MB and B units', async () => {
    mocks.listAssets.mockResolvedValue([
      { ...IMG, size_bytes: 5 * 1024 * 1024 },
      { ...DOC, id: 'a3', name: 'tiny.txt', size_bytes: 500 },
    ]);
    renderPage();
    expect(await screen.findByText(/5\.0 MB/)).toBeTruthy();
    expect(screen.getByText(/500 B/)).toBeTruthy();
  });

  it('shows indexed badge for indexed assets', async () => {
    mocks.listAssets.mockResolvedValue([{ ...DOC, indexed: true }]);
    renderPage();
    await screen.findByTestId('asset-item-a1');
    expect(screen.getByText('indexed')).toBeTruthy();
    expect(screen.queryByTestId('index-a1')).toBeNull();
  });
});
