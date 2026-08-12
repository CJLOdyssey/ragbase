import ModelSelector from '../ModelSelector';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function makeModel(model: string, overrides: Record<string, string> = {}) {
  return { model, keyId: 'k1', ...overrides };
}

const baseProps = {
  selectedModel: '',
  onSelect: vi.fn(),
};

function renderSelector(models: ReturnType<typeof makeModel>[]) {
  return render(<ModelSelector models={models} {...baseProps} />);
}

describe('ModelSelector', { tags: ['unit'] }, () => {
  it('groups models by type', () => {
    renderSelector([
      makeModel('gpt-4o', { type: 'llm' }),
      makeModel('text-embedding-3-small', { type: 'embedding' }),
    ]);
    expect(
      screen.getAllByText('providerEdit.category.llm')[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('providerEdit.category.embedding')[0],
    ).toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('text-embedding-3-small')).toBeInTheDocument();
  });

  it('defaults models without a type to the llm group', () => {
    renderSelector([makeModel('gpt-4o')]);
    expect(
      screen.getAllByText('providerEdit.category.llm')[0],
    ).toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
  });

  it('shows empty-group hint for categories without models', () => {
    renderSelector([makeModel('gpt-4o', { type: 'llm' })]);
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getAllByText('providerEdit.noModelsInGroup').length).toBe(7);
  });

  it('hides groups without hits while searching', () => {
    renderSelector([
      makeModel('gpt-4o', { type: 'llm' }),
      makeModel('text-embedding-3-small', { type: 'embedding' }),
    ]);
    fireEvent.change(screen.getByPlaceholderText('providerEdit.searchModel'), {
      target: { value: 'gpt' },
    });
    expect(
      screen.getAllByText('providerEdit.category.llm')[0],
    ).toBeInTheDocument();
    expect(
      screen.queryAllByText('providerEdit.category.embedding')[0] ?? null,
    ).not.toBeInTheDocument();
    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(
      screen.queryByText('text-embedding-3-small'),
    ).not.toBeInTheDocument();
  });

  it('keeps radio selection behavior', () => {
    renderSelector([
      makeModel('gpt-4o', { type: 'llm' }),
      makeModel('gpt-4o-mini', { type: 'llm' }),
    ]);
    const radios = screen.getAllByRole('radio');
    expect(radios[0]).not.toBeChecked();
    fireEvent.click(radios[0]);
    expect(baseProps.onSelect).toHaveBeenCalledWith('gpt-4o');
  });
});
