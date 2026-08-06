import { TestProviders } from '../../../test/setup';
import ComposerPage from '@/components/content/ComposerPage';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mocks = vi.hoisted(() => ({
  createGeneration: vi.fn(),
  getGeneration: vi.fn(),
  createVariations: vi.fn(),
  generateImage: vi.fn(),
  composeCard: vi.fn(),
  listAssets: vi.fn(),
  uploadAsset: vi.fn(),
  listComposeTemplates: vi.fn(),
  toast: vi.fn(),
}));

vi.mock('@/api/client/generations', () => ({
  createGeneration: mocks.createGeneration,
  getGeneration: mocks.getGeneration,
  createVariations: mocks.createVariations,
  generateImage: mocks.generateImage,
  composeCard: mocks.composeCard,
}));

vi.mock('@/api/client/assets', () => ({
  listAssets: mocks.listAssets,
  uploadAsset: mocks.uploadAsset,
}));

vi.mock('@/api/client/composeTemplates', () => ({
  listComposeTemplates: mocks.listComposeTemplates,
}));

vi.mock('@/utils/useToast', () => ({
  useToast: () => ({ toast: mocks.toast }),
}));

const completedDetail = {
  id: 'run-1',
  session_id: null,
  topic: '夏日咖啡',
  content_type: 'xiaohongshu',
  generation_mode: 'generate',
  status: 'completed',
  result: { title: '标题', summary: '摘要', body_markdown: '正文内容' },
  created_at: null,
};

describe('ComposerPage', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listAssets.mockResolvedValue([]);
    mocks.listComposeTemplates.mockResolvedValue([]);
  });

  it('renders form with content type selector and topic input', () => {
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    expect(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('content.contentType_xiaohongshu'),
    ).toBeInTheDocument();
  });

  it('submits generation with topic payload', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      {
        target: { value: '夏日咖啡' },
      },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await waitFor(() =>
      expect(mocks.createGeneration).toHaveBeenCalledWith({
        contentType: 'xiaohongshu',
        generationMode: 'generate',
        topic: '夏日咖啡',
        additionalRequirements: undefined,
        assetIds: [],
      }),
    );
    await waitFor(() =>
      expect(screen.getByText('正文内容')).toBeInTheDocument(),
    );
  });

  it('does not submit when topic is empty', () => {
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    const btn = screen.getByText('content.generate').closest('button');
    expect(btn).toBeDisabled();
    fireEvent.click(btn as HTMLButtonElement);
    expect(mocks.createGeneration).not.toHaveBeenCalled();
  });

  it('should have no axe violations', async () => {
    const { container } = render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('submits selected content type and extra requirements', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('content.contentType_wechat'));
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '营销文案' } },
    );
    fireEvent.change(screen.getByLabelText('content.input.extraLabel'), {
      target: { value: '语气活泼' },
    });
    fireEvent.click(screen.getByText('content.generate'));
    await waitFor(() =>
      expect(mocks.createGeneration).toHaveBeenCalledWith({
        contentType: 'wechat',
        generationMode: 'generate',
        topic: '营销文案',
        additionalRequirements: '语气活泼',
        assetIds: [],
      }),
    );
  });

  it('shows stop button while running and stops on click', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockReturnValue(new Promise(() => {}));
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    expect(await screen.findByText('content.stop')).toBeInTheDocument();
    fireEvent.click(screen.getByText('content.stop'));
    await waitFor(() => expect(screen.queryByText('content.stop')).toBeNull());
    expect(screen.getByText('content.generate')).toBeInTheDocument();
  });

  it('clears running state when generation fails', async () => {
    mocks.createGeneration.mockRejectedValue(new Error('boom'));
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await waitFor(() => expect(mocks.createGeneration).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByText('content.generating')).toBeNull(),
    );
    expect(screen.getByText('content.generate')).toBeInTheDocument();
  });

  it('generates variants from completed result', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    mocks.createVariations.mockResolvedValue({
      run_id: 'run-2',
      session_id: null,
      status: 'pending',
    });
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await screen.findByText('正文内容');
    fireEvent.click(screen.getByText('content.variants.generateVariant'));
    await waitFor(() =>
      expect(mocks.createVariations).toHaveBeenCalledWith('run-1'),
    );
    expect(screen.getByText('content.variants.generating')).toBeInTheDocument();
  });

  it('resets busy state when variants fail', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    mocks.createVariations.mockRejectedValue(new Error('boom'));
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await screen.findByText('正文内容');
    fireEvent.click(screen.getByText('content.variants.generateVariant'));
    await waitFor(() =>
      expect(screen.queryByText('content.variants.generating')).toBeNull(),
    );
  });

  it('generates image with prompt and selected provider', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await screen.findByText('正文内容');
    const [promptInput, providerSelect] = screen.getAllByLabelText(
      'content.image.prompt',
    );
    fireEvent.change(promptInput, { target: { value: '封面图' } });
    fireEvent.change(providerSelect, { target: { value: 'dashscope' } });
    fireEvent.click(
      screen.getByRole('button', { name: 'content.image.generate' }),
    );
    await waitFor(() =>
      expect(mocks.generateImage).toHaveBeenCalledWith('run-1', {
        prompt: '封面图',
        provider: 'dashscope',
      }),
    );
  });

  it('disables image generate button without prompt', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await screen.findByText('正文内容');
    expect(
      screen.getByRole('button', { name: 'content.image.generate' }),
    ).toBeDisabled();
  });

  it('opens compose modal from result viewer', async () => {
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    mocks.getGeneration.mockResolvedValue(completedDetail);
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await screen.findByText('正文内容');
    fireEvent.click(
      screen.getByRole('button', { name: 'content.card.compose' }),
    );
    expect(
      await screen.findByRole('dialog', { name: 'content.card.compose' }),
    ).toBeInTheDocument();
  });

  it('toggles asset selection and includes it in generation', async () => {
    mocks.listAssets.mockResolvedValue([
      {
        id: 'a1',
        name: '素材.md',
        asset_type: 'document',
        size_bytes: 100,
        usage_count: 0,
        indexed: false,
      },
    ]);
    mocks.createGeneration.mockResolvedValue({
      run_id: 'run-1',
      session_id: null,
      status: 'pending',
    });
    render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    await screen.findByText('素材.md');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.change(
      screen.getByPlaceholderText('content.input.topicPlaceholder'),
      { target: { value: '夏日咖啡' } },
    );
    fireEvent.click(screen.getByText('content.generate'));
    await waitFor(() =>
      expect(mocks.createGeneration).toHaveBeenCalledWith({
        contentType: 'xiaohongshu',
        generationMode: 'generate',
        topic: '夏日咖啡',
        additionalRequirements: undefined,
        assetIds: ['a1'],
      }),
    );
  });

  it('shows success toast and refetches after picker upload', async () => {
    const { container } = render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    await screen.findByText('assets.list.empty');
    const input = container.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
    const file = new File([new Uint8Array(1024)], 'a.md', {
      type: 'text/markdown',
    });
    fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });
    await waitFor(() => expect(mocks.uploadAsset).toHaveBeenCalledWith(file));
    await waitFor(() =>
      expect(mocks.toast).toHaveBeenCalledWith(
        'assets.upload.success',
        'success',
      ),
    );
    await waitFor(() => expect(mocks.listAssets).toHaveBeenCalledTimes(2));
  });

  it('shows error toast when picker upload fails', async () => {
    mocks.uploadAsset.mockRejectedValue(new Error('boom'));
    const { container } = render(
      <TestProviders>
        <ComposerPage />
      </TestProviders>,
    );
    await screen.findByText('assets.list.empty');
    const input = container.querySelector('input[type="file"]');
    const file = new File([new Uint8Array(1024)], 'a.md', {
      type: 'text/markdown',
    });
    fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });
    await waitFor(() =>
      expect(mocks.toast).toHaveBeenCalledWith('assets.upload.failed', 'error'),
    );
  });
});
