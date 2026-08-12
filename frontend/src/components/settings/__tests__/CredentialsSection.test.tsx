import CredentialsSection from '../CredentialsSection';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

function renderSection(extra: Record<string, unknown> = {}) {
  return render(
    <CredentialsSection
      name=""
      baseUrl=""
      apiKey=""
      showKey={false}
      onChangeName={vi.fn()}
      onChangeBaseUrl={vi.fn()}
      onChangeApiKey={vi.fn()}
      onToggleShowKey={vi.fn()}
      {...extra}
    />,
  );
}

describe('CredentialsSection', () => {
  it('renders name, baseUrl and apiKey fields', () => {
    renderSection();
    expect(
      screen.getByPlaceholderText('providerEdit.name'),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('providerEdit.baseUrlPlaceholder'),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('providerEdit.apiKeyPlaceholder'),
    ).toBeInTheDocument();
    expect(screen.getByText('providerEdit.apiKey')).toBeInTheDocument();
  });

  it('hides baseUrl when hideBaseUrl is set', () => {
    renderSection({ hideBaseUrl: true });
    expect(
      screen.queryByPlaceholderText('providerEdit.baseUrlPlaceholder'),
    ).not.toBeInTheDocument();
  });

  it('api key input is password type by default and toggles to text', () => {
    const onToggleShowKey = vi.fn();
    renderSection({ onToggleShowKey });
    const input = screen.getByPlaceholderText(
      'providerEdit.apiKeyPlaceholder',
    ) as HTMLInputElement;
    expect(input.type).toBe('password');
    fireEvent.click(screen.getByRole('button', { name: 'Show API key' }));
    expect(onToggleShowKey).toHaveBeenCalled();
  });

  it('shows text input and hide button when showKey', () => {
    renderSection({ showKey: true });
    const input = screen.getByPlaceholderText(
      'providerEdit.apiKeyPlaceholder',
    ) as HTMLInputElement;
    expect(input.type).toBe('text');
    expect(
      screen.getByRole('button', { name: 'Hide API key' }),
    ).toBeInTheDocument();
  });

  it('propagates input changes to callbacks', () => {
    const onChangeName = vi.fn();
    const onChangeBaseUrl = vi.fn();
    const onChangeApiKey = vi.fn();
    renderSection({ onChangeName, onChangeBaseUrl, onChangeApiKey });
    fireEvent.change(screen.getByPlaceholderText('providerEdit.name'), {
      target: { value: 'n1' },
    });
    fireEvent.change(
      screen.getByPlaceholderText('providerEdit.baseUrlPlaceholder'),
      { target: { value: 'b1' } },
    );
    fireEvent.change(
      screen.getByPlaceholderText('providerEdit.apiKeyPlaceholder'),
      { target: { value: 'k1' } },
    );
    expect(onChangeName).toHaveBeenCalledWith('n1');
    expect(onChangeBaseUrl).toHaveBeenCalledWith('b1');
    expect(onChangeApiKey).toHaveBeenCalledWith('k1');
  });
});
