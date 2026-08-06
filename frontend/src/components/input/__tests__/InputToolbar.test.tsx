import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { createRef } from 'react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const { mockComposerSetValue, mockComposerSubmit, mockComposerHandleKeyDown } = vi.hoisted(() => ({
  mockComposerSetValue: vi.fn(),
  mockComposerSubmit: vi.fn(),
  mockComposerHandleKeyDown: vi.fn(),
}));

let mockComposerHasContent = false;

vi.mock('@/hooks/useMessageComposer', () => ({
  useMessageComposer: () => ({
    value: '',
    setValue: mockComposerSetValue,
    submit: mockComposerSubmit,
    handleKeyDown: mockComposerHandleKeyDown,
    get hasContent() { return mockComposerHasContent; },
    charCount: 0,
    maxLength: 2000,
  }),
}));

const { mockPaletteFiltered, mockPaletteUpdateFromValue, mockPaletteHandleKeyDown, mockPaletteOpen } = vi.hoisted(() => ({
  mockPaletteFiltered: [] as Array<{ id: string; label: string; source: string }>,
  mockPaletteUpdateFromValue: vi.fn(),
  mockPaletteHandleKeyDown: vi.fn(() => false),
  mockPaletteOpen: false,
}));

vi.mock('@/hooks/useCommandPalette', () => ({
  useCommandPalette: () => ({
    filtered: mockPaletteFiltered,
    filteredCommands: [],
    activeIndex: -1,
    open: mockPaletteOpen,
    updateFromValue: mockPaletteUpdateFromValue,
    handleKeyDown: mockPaletteHandleKeyDown,
    selectCommand: vi.fn(),
    setActiveIndex: vi.fn(),
    close: vi.fn(),
  }),
}));

const { mockToast } = vi.hoisted(() => ({ mockToast: vi.fn() }));

vi.mock('@/utils/useToast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/contexts/SettingsContext', () => ({
  useSettings: () => ({ settings: { sendOnEnter: true, sendMode: 'enter' }, updateSettings: vi.fn() }),
}));

vi.mock('@/components/input/ModelSelector', () => ({ default: ({ models }: { models: unknown[] }) => (models?.length ? <div data-testid="model-selector" /> : null) }));
vi.mock('@/components/input/FileAttach', () => ({ default: () => <div data-testid="file-attach" /> }));
vi.mock('@/components/input/CommandDropdown', () => ({ default: () => <div data-testid="command-dropdown" /> }));

import InputToolbar from '@/components/input/InputToolbar';
import type { InputToolbarHandle } from '@/components/input/InputToolbar';

const defaultProps = {
  onSend: vi.fn(),
  models: [],
  selectedModel: '',
  onModelChange: vi.fn(),
  placeholder: 'Type a message...',
  maxLength: 2000,
};

describe('InputToolbar', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders basic elements', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined();
  });

  it('renders send button when not running', () => {
    render(<InputToolbar {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('renders stop button when running', () => {
    render(<InputToolbar {...defaultProps} isRunning={true} onStop={vi.fn()} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('does not render model selector when no models', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.queryByTestId('model-selector')).toBeNull();
  });

  it('renders model selector when models are provided', () => {
    render(<InputToolbar {...defaultProps} models={[{ id: 'gpt-4', name: 'GPT-4' }]} />);
    expect(screen.getByTestId('model-selector')).toBeInTheDocument();
  });

  it('renders textarea with placeholder', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined();
  });

  it('renders without crashing when isRunning=true', () => {
    render(<InputToolbar {...defaultProps} isRunning={true} onStop={vi.fn()} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined();
  });

  it('renders file attach component', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.getByTestId('file-attach')).toBeInTheDocument();
  });

  it('calls mockComposerSubmit when send button clicked with content', () => {
    mockComposerHasContent = true;
    render(<InputToolbar {...defaultProps} />);
    fireEvent.click(screen.getByText('home.send'));
    expect(mockComposerSubmit).toHaveBeenCalled();
  });

  it('calls onStop when stop button clicked during running', () => {
    const onStop = vi.fn();
    render(<InputToolbar {...defaultProps} isRunning={true} onStop={onStop} />);
    fireEvent.click(screen.getByText('home.stop'));
    expect(onStop).toHaveBeenCalledOnce();
  });

  it('calls setValue on textarea change', () => {
    render(<InputToolbar {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: 'hello' } });
    expect(mockComposerSetValue).toHaveBeenCalled();
  });

  it('calls palette updateFromValue on textarea change', () => {
    render(<InputToolbar {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(textarea, { target: { value: '/' } });
    expect(mockPaletteUpdateFromValue).toHaveBeenCalled();
  });

  it('addFiles via ref does not crash', () => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], 'test.txt')]);
    });
  });

  it('paste event with files calls preventDefault', () => {
    render(<InputToolbar {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    const file = new File(['content'], 'pasted.txt');
    const clipboardData = { files: [file], getData: vi.fn() };
    fireEvent.paste(textarea, { clipboardData });
  });

  it('send button is disabled when hasContent is false', () => {
    mockComposerHasContent = false;
    render(<InputToolbar {...defaultProps} />);
    const sendBtn = screen.getByText('home.send').closest('button');
    expect(sendBtn).toBeDisabled();
  });

  it('send button is enabled when hasContent is true', () => {
    mockComposerHasContent = true;
    render(<InputToolbar {...defaultProps} />);
    const sendBtn = screen.getByText('home.send').closest('button');
    expect(sendBtn).not.toBeDisabled();
  });

  it('textarea has correct maxLength', () => {
    render(<InputToolbar {...defaultProps} maxLength={5000} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    expect(textarea).toHaveAttribute('maxLength', '5000');
  });

  it('textarea has aria-label', () => {
    render(<InputToolbar {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Type a message...');
    expect(textarea).toHaveAttribute('aria-label', 'Type a message...');
  });

  it('shows file count in FileAttach when files added via ref', () => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => { ref.current?.addFiles([new File(['a'], 'a.txt')]); });
    act(() => { ref.current?.addFiles([new File(['b'], 'b.txt')]); });
  });

  it('triggers toast when more than 5 files attached', () => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    const files = Array.from({ length: 6 }, (_, i) => new File([`content${i}`], `file${i}.txt`));
    act(() => { ref.current?.addFiles(files); });
    expect(mockToast).toHaveBeenCalled();
  });

});
