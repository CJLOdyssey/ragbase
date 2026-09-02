import { createRef } from 'react';
import HomeScreen from '../HomeScreen';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, fallback?: string) => fallback ?? k,
    i18n: { language: 'zh-CN' },
  }),
}));

vi.mock('../../input/InputToolbar', () => ({
  default: () => <div data-testid="mock-input-toolbar">toolbar</div>,
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    button: ({
      children,
      onClick,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
    }) => (
      <button type="button" onClick={onClick}>
        {children}
      </button>
    ),
  },
  useReducedMotion: () => false,
}));

vi.mock('../GreetingAnimation', () => ({
  default: () => <h1>home.greeting</h1>,
}));

function renderHome(extra: Record<string, unknown> = {}) {
  return render(
    <HomeScreen
      conversationKey={0}
      models={[]}
      selectedModel=""
      onModelChange={vi.fn()}
      commands={[]}
      onSend={vi.fn()}
      inputToolbarRef={createRef()}
      {...extra}
    />,
  );
}

describe('HomeScreen', () => {
  it('renders subtitle and input toolbar', () => {
    renderHome();
    expect(screen.getByText('home.subtitle')).toBeInTheDocument();
    expect(screen.getByTestId('mock-input-toolbar')).toBeInTheDocument();
  });

  it('shows the greeting heading', () => {
    renderHome();
    expect(screen.getByText('home.greeting')).toBeInTheDocument();
  });

  it('hides feature buttons when no commands are wired (no dead UI)', () => {
    renderHome();
    expect(screen.queryByText('Search')).not.toBeInTheDocument();
  });

  it('fires onExecuteCommand for each feature button', () => {
    const onExecuteCommand = vi.fn();
    renderHome({ commands: [{ id: 'search', label: 'search', source: 'local' }], onExecuteCommand });
    fireEvent.click(screen.getByText('Search'));
    expect(onExecuteCommand).toHaveBeenCalledWith('search');
    fireEvent.click(screen.getByText('Data'));
    expect(onExecuteCommand).toHaveBeenCalledWith('data');
    fireEvent.click(screen.getByText('Documents'));
    expect(onExecuteCommand).toHaveBeenCalledWith('document');
    fireEvent.click(screen.getByText('Images'));
    expect(onExecuteCommand).toHaveBeenCalledWith('image');
    fireEvent.click(screen.getByText('More'));
    expect(onExecuteCommand).toHaveBeenCalledWith('more');
    expect(onExecuteCommand).toHaveBeenCalledTimes(5);
  });

  it('uses i18n fallback labels for feature buttons', () => {
    renderHome({ commands: [{ id: 'search', label: 'search', source: 'local' }], onExecuteCommand: vi.fn() });
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Data')).toBeInTheDocument();
    expect(screen.getByText('More')).toBeInTheDocument();
  });
});
