import { TestProviders } from '../../../test/setup';
import type { ComposeTemplate } from '../../../types/generation';
import ComposePreview from '../ComposePreview';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mocks = vi.hoisted(() => ({
  composeCard: vi.fn(),
  listComposeTemplates: vi.fn(),
}));

vi.mock('../../../api/client/generations', () => ({
  composeCard: mocks.composeCard,
}));

vi.mock('../../../api/client/composeTemplates', () => ({
  listComposeTemplates: mocks.listComposeTemplates,
}));

const TEMPLATES: ComposeTemplate[] = [
  { id: 't1', name: '模板A', layout: {}, is_default: true },
  { id: 't2', name: '模板B', layout: {}, is_default: false },
];

function renderPreview() {
  return render(
    <TestProviders>
      <ComposePreview
        runId="run-1"
        defaultTitle="默认标题"
        defaultSummary="默认摘要"
        onClose={vi.fn()}
      />
    </TestProviders>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listComposeTemplates.mockResolvedValue(TEMPLATES);
});

describe('ComposePreview', { tags: ['unit'] }, () => {
  it('loads templates and selects the default one', async () => {
    renderPreview();
    expect(await screen.findByText('模板A')).toBeInTheDocument();
    expect(screen.getByText('模板B')).toBeInTheDocument();
    const select = screen.getByLabelText(
      'content.card.selectTemplate',
    ) as HTMLSelectElement;
    expect(select.value).toBe('t1');
    expect(screen.getByLabelText('content.card.titleLabel')).toHaveValue(
      '默认标题',
    );
    expect(screen.getByLabelText('content.card.summaryLabel')).toHaveValue(
      '默认摘要',
    );
    expect(
      screen.getByRole('button', { name: 'content.card.compose' }),
    ).toBeEnabled();
  });

  it('composes card with template, title and summary', async () => {
    mocks.composeCard.mockResolvedValue({
      template: TEMPLATES[0],
      fields: { title: '新标题', summary: '新摘要', image_attachment_ids: [] },
    });
    renderPreview();
    await screen.findByText('模板A');
    fireEvent.change(screen.getByLabelText('content.card.titleLabel'), {
      target: { value: '新标题' },
    });
    fireEvent.change(screen.getByLabelText('content.card.summaryLabel'), {
      target: { value: '新摘要' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'content.card.compose' }),
    );
    await waitFor(() =>
      expect(mocks.composeCard).toHaveBeenCalledWith('run-1', {
        templateId: 't1',
        title: '新标题',
        summary: '新摘要',
      }),
    );
    expect(await screen.findByTestId('compose-result')).toBeInTheDocument();
    const preview = within(screen.getByTestId('compose-result'));
    expect(
      preview.getByText('content.card.preview · 模板A'),
    ).toBeInTheDocument();
    expect(preview.getByText('新标题')).toBeInTheDocument();
    expect(preview.getByText('新摘要')).toBeInTheDocument();
  });

  it('shows error toast when compose fails', async () => {
    mocks.composeCard.mockRejectedValue(new Error('boom'));
    renderPreview();
    await screen.findByText('模板A');
    fireEvent.click(
      screen.getByRole('button', { name: 'content.card.compose' }),
    );
    expect(await screen.findByText('assets.upload.failed')).toBeInTheDocument();
    expect(screen.queryByTestId('compose-result')).toBeNull();
  });

  it('disables compose button when no templates loaded', async () => {
    mocks.listComposeTemplates.mockResolvedValue([]);
    renderPreview();
    expect(
      await screen.findByLabelText('content.card.selectTemplate'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'content.card.compose' }),
    ).toBeDisabled();
  });

  it('should have no axe violations', async () => {
    const { container } = renderPreview();
    await screen.findByText('模板A');
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
