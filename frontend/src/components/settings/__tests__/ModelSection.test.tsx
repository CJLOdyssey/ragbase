import ModelSection from '../ModelSection';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, opts?: { name?: string }) =>
      opts?.name ? `${k}:${opts.name}` : k,
  }),
}));

function makeProps(overrides: Record<string, unknown> = {}) {
  return {
    models: ['gpt-4'],
    modelTypes: { 'gpt-4': 'llm' },
    typeDefaults: {},
    fetching: false,
    apiKey: 'sk-test',
    onRemoveModel: vi.fn(),
    onFetchModels: vi.fn(),
    onChangeModelType: vi.fn(),
    ...overrides,
  };
}

describe('ModelSection', { tags: ['unit'] }, () => {
  it('renders model rows with type select and remove button', () => {
    render(<ModelSection {...makeProps()} />);
    expect(
      screen.getByText('providerEdit.supportedModels'),
    ).toBeInTheDocument();
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
    const typeSelect = screen.getByRole('combobox', {
      name: 'providerEdit.modelTypeOf:gpt-4',
    });
    expect(typeSelect).toHaveValue('llm');
  });

  it('falls back to typeDefaults when a model has no stored type', () => {
    render(
      <ModelSection
        {...makeProps({
          modelTypes: {},
          typeDefaults: { 'gpt-4': 'llm' },
        })}
      />,
    );
    expect(
      screen.getByRole('combobox', { name: 'providerEdit.modelTypeOf:gpt-4' }),
    ).toHaveValue('llm');
  });

  it('fires change and remove handlers', () => {
    const props = makeProps();
    render(<ModelSection {...props} />);
    fireEvent.change(
      screen.getByRole('combobox', { name: 'providerEdit.modelTypeOf:gpt-4' }),
      { target: { value: 'embedding' } },
    );
    expect(props.onChangeModelType).toHaveBeenCalledWith('gpt-4', 'embedding');
    fireEvent.click(screen.getByTitle('providerEdit.fetchFromApi'));
    expect(props.onFetchModels).toHaveBeenCalled();
  });

  it('shows the with-key hint when no models but apiKey present', () => {
    render(<ModelSection {...makeProps({ models: [] })} />);
    expect(
      screen.getByText('providerEdit.noModelsWithKey'),
    ).toBeInTheDocument();
  });

  it('shows the enter-key hint when no models and no apiKey', () => {
    render(<ModelSection {...makeProps({ models: [], apiKey: '' })} />);
    expect(
      screen.getByText('providerEdit.enterApiKeyToFetch'),
    ).toBeInTheDocument();
  });

  it('disables the fetch button without apiKey or while fetching', () => {
    const noKey = makeProps({ apiKey: '  ' });
    const { rerender } = render(<ModelSection {...noKey} />);
    expect(
      (screen.getByTitle('providerEdit.fetchFromApi') as HTMLButtonElement)
        .disabled,
    ).toBe(true);

    const fetching = makeProps({ fetching: true });
    rerender(<ModelSection {...fetching} />);
    expect(
      (screen.getByTitle('providerEdit.fetchFromApi') as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it('remove button triggers onRemoveModel per model', () => {
    const props = makeProps({ models: ['a', 'b'] });
    render(<ModelSection {...props} />);
    const removeBtns = screen.getAllByTitle('providerEdit.fetchFromApi');
    // 移除按钮是每行 X 图标（无 title），fetch 按钮有 title —— 直接按行找
    const rows = screen.getAllByText(/^[ab]$/);
    expect(rows).toHaveLength(2);
    // X 按钮无文本，用行内 button 定位
    const rowA = screen.getByText('a').closest('div')!.parentElement!;
    const xBtn = rowA.querySelector('button')!;
    fireEvent.click(xBtn);
    expect(props.onRemoveModel).toHaveBeenCalledWith('a');
    void removeBtns;
  });
});
