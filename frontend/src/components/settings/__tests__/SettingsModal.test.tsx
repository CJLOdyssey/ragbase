import { changeLanguage } from '../../../i18n/index';
import { TestProviders } from '../../../test/setup';
import SettingsModal from '../SettingsModal';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

vi.mock('../../../i18n/index', () => ({
  changeLanguage: vi.fn(),
  default: { t: (k: string) => k, language: 'zh-CN' },
}));

function renderModal() {
  return render(
    <TestProviders>
      <SettingsModal onClose={vi.fn()} />
    </TestProviders>,
  );
}

describe('SettingsModal', { tags: ['unit'] }, () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders the general tab with language and appearance controls', () => {
    renderModal();
    expect(screen.getByText('settings.title')).toBeInTheDocument();
    // tab 按钮 + 区块标题各出现一次
    expect(
      screen.getAllByText('settings.general').length,
    ).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('settings.language')).toBeInTheDocument();
    expect(screen.getByText('settings.theme')).toBeInTheDocument();
    expect(screen.getByText('settings.fontSize')).toBeInTheDocument();
    expect(screen.getByText('16px')).toBeInTheDocument();
    expect(screen.getByText('settings.autoSave')).toBeInTheDocument();
    expect(screen.getByText('settings.streamOutput')).toBeInTheDocument();
  });

  it('switches to the about tab and back', () => {
    renderModal();
    fireEvent.click(screen.getAllByText('settings.about')[0]);
    expect(screen.getAllByText('settings.about').length).toBeGreaterThanOrEqual(
      2,
    );
    expect(screen.getByText('RagBase')).toBeInTheDocument();
    expect(screen.getByText('v 1.0.0')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
    fireEvent.click(screen.getAllByText('settings.general')[0]);
    expect(screen.getByText('settings.language')).toBeInTheDocument();
  });

  it('language select calls changeLanguage', () => {
    renderModal();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'en-US' } });
    expect(changeLanguage).toHaveBeenCalledWith('en-US');
  });

  it('theme select updates settings', () => {
    renderModal();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: 'light' } });
    expect(selects[1]).toHaveValue('light');
  });

  it('font size range updates the settings', () => {
    renderModal();
    const range = screen.getByRole('slider');
    fireEvent.change(range, { target: { value: '20' } });
    expect(screen.getByText('20px')).toBeInTheDocument();
  });

  it('send mode select updates settings', () => {
    renderModal();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[2], { target: { value: 'ctrl-enter' } });
    expect(selects[2]).toHaveValue('ctrl-enter');
  });

  it('autoSave and streamOutput toggles flip the switches', () => {
    renderModal();
    const toggles = screen.getAllByRole('checkbox');
    expect(toggles).toHaveLength(2);
    fireEvent.click(toggles[0]);
    expect(toggles[0]).not.toBeChecked();
    fireEvent.click(toggles[1]);
    expect(toggles[1]).not.toBeChecked();
  });

  it('footer buttons close the modal', () => {
    const onClose = vi.fn();
    render(
      <TestProviders>
        <SettingsModal onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('settings.cancel'));
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('settings.save'));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
