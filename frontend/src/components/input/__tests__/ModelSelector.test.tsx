import ModelSelector from '@/components/input/ModelSelector';
import { TestProviders } from '@/test/setup';
import type { ModelOption } from '@/types/input';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

function makeModel(
  id: string,
  overrides: Partial<ModelOption> = {},
): ModelOption {
  return {
    id,
    label: 'Model ' + id,
    provider: 'provider-a',
    ...overrides,
  };
}

describe('ModelSelector', { tags: ['unit'] }, () => {
  const onChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders configure button when no models', () => {
    const onConfigure = vi.fn();
    render(
      <TestProviders>
        <ModelSelector
          models={[]}
          selectedModel=""
          onChange={onChange}
          onConfigure={onConfigure}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onConfigure).toHaveBeenCalled();
  });

  it('renders selected model label', () => {
    const models = [makeModel('m1'), makeModel('m2')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    expect(screen.getByText('Model m1')).toBeInTheDocument();
  });

  it('opens dropdown on click', () => {
    const models = [makeModel('m1'), makeModel('m2')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Model m2')).toBeInTheDocument();
  });

  it('selects a model from dropdown', () => {
    const models = [makeModel('m1'), makeModel('m2')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText('Model m2'));
    expect(onChange).toHaveBeenCalledWith('m2');
  });

  it('shows deprecated status', () => {
    const models = [makeModel('m1', { status: 'deprecated' as const })];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('已弃用')).toBeInTheDocument();
  });

  it('shows sunset status', () => {
    const models = [makeModel('m1', { status: 'sunset' as const })];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('即将下线')).toBeInTheDocument();
  });

  it('groups models by provider', () => {
    const models = [
      makeModel('m1', { provider: 'OpenAI' }),
      makeModel('m2', { provider: 'OpenAI' }),
      makeModel('m3', { provider: 'Anthropic' }),
    ];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('closes dropdown on Escape key', () => {
    const models = [makeModel('m1'), makeModel('m2')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Model m2')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByText('Model m2')).not.toBeInTheDocument();
  });

  it('shows recent models group at top without duplicates', () => {
    localStorage.setItem('ragbase-recent-models', JSON.stringify(['m2', 'm1']));
    const models = [makeModel('m1'), makeModel('m2'), makeModel('m3')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(3);
    expect(screen.getByText('最近使用')).toBeInTheDocument();
    const recent = screen.getByText('最近使用').parentElement!;
    expect(recent.textContent).toContain('Model m2');
    expect(recent.textContent).toContain('Model m1');
    expect(recent.textContent).not.toContain('Model m3');
  });

  it('records selection into recent list', () => {
    const models = [makeModel('m1'), makeModel('m2'), makeModel('m3')];
    render(
      <TestProviders>
        <ModelSelector models={models} selectedModel="m1" onChange={onChange} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText('Model m3'));
    expect(JSON.parse(localStorage.getItem('ragbase-recent-models')!)).toEqual([
      'm3',
    ]);
  });
});
