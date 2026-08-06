import { TestProviders } from '../../../test/setup';
import SettingsPage from '../SettingsPage';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

const mocks = vi.hoisted(() => ({
  listKeys: vi.fn(),
  createKey: vi.fn(),
  deleteKey: vi.fn(),
  testKeyConnection: vi.fn(),
}));

vi.mock('../../../api/client/keys', () => ({
  listKeys: mocks.listKeys,
  createKey: mocks.createKey,
  deleteKey: mocks.deleteKey,
  testKeyConnection: mocks.testKeyConnection,
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('../../../utils/useToast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const keyItem = {
  id: 'k1',
  provider: 'deepseek',
  usage_type: 'chat',
  label: '生产',
  key_masked: 'sk-***abc',
  base_url: null,
  models: ['deepseek-chat'],
  is_active: true,
  is_default: true,
  last_used_at: null,
  created_at: '2026-08-06T00:00:00Z',
};

function renderPage() {
  return render(
    <TestProviders>
      <SettingsPage />
    </TestProviders>,
  );
}

describe('SettingsPage', { tags: ['unit'] }, () => {
  beforeEach(() => {
    mocks.listKeys.mockResolvedValue([]);
    mocks.createKey.mockResolvedValue(keyItem);
    mocks.deleteKey.mockResolvedValue(undefined);
    mocks.testKeyConnection.mockResolvedValue({ success: true, message: 'ok' });
  });

  it('renders empty state and hint', async () => {
    renderPage();
    expect(await screen.findByText('settings.empty')).toBeTruthy();
    expect(screen.getByText('settings.apiKeyHint')).toBeTruthy();
  });

  it('shows key list with provider, masked key and models', async () => {
    mocks.listKeys.mockResolvedValue([keyItem]);
    renderPage();
    expect(await screen.findByText('生产')).toBeTruthy();
    expect(screen.getByText(/deepseek · sk-\*\*\*abc/)).toBeTruthy();
    expect(screen.getByText('settings.default')).toBeTruthy();
  });

  it('creates a key from the form', async () => {
    renderPage();
    fireEvent.click(await screen.findByText('settings.add'));
    fireEvent.change(
      screen.getByPlaceholderText('settings.providerPlaceholder'),
      {
        target: { value: 'deepseek' },
      },
    );
    fireEvent.change(screen.getByPlaceholderText('settings.labelPlaceholder'), {
      target: { value: '生产' },
    });
    fireEvent.change(
      screen.getByPlaceholderText('settings.apiKeyPlaceholder'),
      {
        target: { value: 'sk-test' },
      },
    );
    fireEvent.change(
      screen.getByPlaceholderText('settings.modelsPlaceholder'),
      {
        target: { value: 'deepseek-chat, deepseek-reasoner' },
      },
    );
    fireEvent.click(screen.getByText('settings.save'));
    await waitFor(() =>
      expect(mocks.createKey).toHaveBeenCalledWith({
        provider: 'deepseek',
        label: '生产',
        api_key: 'sk-test',
        base_url: undefined,
        models: ['deepseek-chat', 'deepseek-reasoner'],
      }),
    );
  });

  it('deletes a key', async () => {
    mocks.listKeys.mockResolvedValue([keyItem]);
    renderPage();
    await screen.findByText('生产');
    fireEvent.click(screen.getByLabelText('settings.deleteSuccess: 生产'));
    await waitFor(() => expect(mocks.deleteKey).toHaveBeenCalledWith('k1'));
  });

  it('tests key connection', async () => {
    mocks.listKeys.mockResolvedValue([keyItem]);
    renderPage();
    await screen.findByText('生产');
    fireEvent.click(screen.getByLabelText('settings.test: 生产'));
    await waitFor(() =>
      expect(mocks.testKeyConnection).toHaveBeenCalledWith('k1'),
    );
  });

  it('has no axe violations', async () => {
    const { container } = renderPage();
    await screen.findByText('settings.empty');
    expect(await axe(container)).toHaveNoViolations();
  });
});
