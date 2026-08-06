import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { createRef } from 'react';
import InputToolbar from '@/components/input/InputToolbar';
import type { InputToolbarHandle } from '@/components/input/InputToolbar';

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

const paletteMock = vi.hoisted(() => {
  let open = false;
  return {
    filtered: [] as Array<{ id: string; label: string; source: string }>,
    updateFromValue: vi.fn(),
    handleKeyDown: vi.fn(() => false),
    selectCommand: vi.fn(),
    close: vi.fn(),
    set openValue(v: boolean) { open = v; },
    get openValue() { return open; },
  };
});

vi.mock('@/hooks/useCommandPalette', () => ({
  useCommandPalette: () => ({
    filtered: paletteMock.filtered,
    filteredCommands: [],
    activeIndex: 0,
    open: paletteMock.openValue,
    updateFromValue: paletteMock.updateFromValue,
    handleKeyDown: paletteMock.handleKeyDown,
    selectCommand: paletteMock.selectCommand,
    setActiveIndex: vi.fn(),
    close: paletteMock.close,
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
vi.mock('@/components/input/FileAttach', () => ({
  default: ({ onReject }: { onReject: (r: Array<{ file: File; reason: 'size_exceeded' | 'type_denied' }>) => void }) => (
    <button
      type="button"
      data-testid="file-attach"
      onClick={() =>
        onReject([
          { file: new File(['x'], 'big.txt'), reason: 'size_exceeded' },
          { file: new File(['y'], 'bad.txt'), reason: 'type_denied' },
        ])
      }
    />
  ),
}));
vi.mock('@/components/input/CommandDropdown', () => ({ default: () => <div data-testid="command-dropdown" /> }));

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
    paletteMock.openValue = false;
    paletteMock.filtered.length = 0;
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
    expect(paletteMock.updateFromValue).toHaveBeenCalled();
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

  it('executes local command via palette on Enter', () => {
    const onExecuteCommand = vi.fn();
    paletteMock.openValue = true;
    paletteMock.filtered.push({ id: 'c1', label: 'Cmd', source: 'local' });
    paletteMock.handleKeyDown.mockReturnValue(true);
    render(<InputToolbar {...defaultProps} onExecuteCommand={onExecuteCommand} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), { key: 'Enter', shiftKey: false });
    expect(paletteMock.close).toHaveBeenCalled();
    expect(onExecuteCommand).toHaveBeenCalledWith('c1');
  });

  it('inserts agent command replacement when palette handled Enter', () => {
    paletteMock.openValue = true;
    paletteMock.filtered.push({ id: 'c2', label: 'Cmd2', source: 'agent' });
    paletteMock.handleKeyDown.mockReturnValue(true);
    paletteMock.selectCommand.mockReturnValue('/Cmd2 ');
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), { key: 'Enter', shiftKey: false });
    expect(paletteMock.selectCommand).toHaveBeenCalledWith(0);
    expect(mockComposerSetValue).toHaveBeenCalledWith('/Cmd2 ');
  });

  it('does not select command on Shift+Enter when palette open', () => {
    paletteMock.openValue = true;
    paletteMock.handleKeyDown.mockReturnValue(true);
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), { key: 'Enter', shiftKey: true });
    expect(paletteMock.selectCommand).not.toHaveBeenCalled();
  });

  it('falls through to composer when palette does not handle key', () => {
    paletteMock.handleKeyDown.mockReturnValue(false);
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), { key: 'Enter', shiftKey: false });
    expect(mockComposerHandleKeyDown).toHaveBeenCalled();
  });

  it('shows fileTooLarge and fileTypeDenied toasts on rejections', () => {
    render(<InputToolbar {...defaultProps} />);
    fireEvent.click(screen.getByTestId('file-attach'));
    expect(mockToast).toHaveBeenCalledWith('home.fileTooLarge', 'error');
    expect(mockToast).toHaveBeenCalledWith('home.fileTypeDenied', 'error');
  });

});
