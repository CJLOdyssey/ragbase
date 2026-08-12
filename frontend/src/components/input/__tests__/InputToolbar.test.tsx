import { createRef } from 'react';
import InputToolbar, {
  type InputToolbarHandle,
} from '@/components/input/InputToolbar';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  mockComposerHandleKeyDown,
  mockComposerSetValue,
  mockComposerSubmit,
  mockDeleteAttachment,
  mockToast,
  mockUploadAttachment,
  paletteMock,
  setMockComposerHasContent,
} from './helpers/inputToolbarTestSetup';

// vi.mock is hoisted above ALL imports — factories cannot reference top-level
// bindings directly, so async factories re-import the shared mock helpers.
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('@/hooks/useMessageComposer', async () => {
  const h = await import('./helpers/inputToolbarTestSetup');
  return {
    useMessageComposer: () => ({
      value: '',
      setValue: h.mockComposerSetValue,
      submit: h.mockComposerSubmit,
      handleKeyDown: h.mockComposerHandleKeyDown,
      get hasContent() {
        return h.getComposerHasContent();
      },
      charCount: 0,
      maxLength: 2000,
    }),
  };
});

vi.mock('@/hooks/useCommandPalette', async () => {
  const h = await import('./helpers/inputToolbarTestSetup');
  return {
    useCommandPalette: () => ({
      filtered: h.paletteMock.filtered,
      filteredCommands: [],
      activeIndex: 0,
      open: h.paletteMock.openValue,
      updateFromValue: h.paletteMock.updateFromValue,
      handleKeyDown: h.paletteMock.handleKeyDown,
      selectCommand: h.paletteMock.selectCommand,
      setActiveIndex: vi.fn(),
      close: h.paletteMock.close,
    }),
  };
});

vi.mock('@/utils/useToast', async () => {
  const h = await import('./helpers/inputToolbarTestSetup');
  return {
    useToast: () => ({ toast: h.mockToast }),
  };
});

vi.mock('@/api/client/attachments', async () => {
  const h = await import('./helpers/inputToolbarTestSetup');
  return {
    uploadAttachment: h.mockUploadAttachment,
    deleteAttachment: h.mockDeleteAttachment,
  };
});

vi.mock('@/contexts/SettingsContext', () => ({
  useSettings: () => ({
    settings: { sendOnEnter: true, sendMode: 'enter' },
    updateSettings: vi.fn(),
  }),
}));

vi.mock('@/components/input/ModelSelector', () => ({
  default: ({ models }: { models: unknown[] }) =>
    models?.length ? <div data-testid="model-selector" /> : null,
}));

vi.mock('@/components/input/FileAttach', () => ({
  default: ({
    onReject,
  }: {
    onReject: (
      r: Array<{ file: File; reason: 'size_exceeded' | 'type_denied' }>,
    ) => void;
  }) => (
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

vi.mock('@/components/input/CommandDropdown', () => ({
  default: () => <div data-testid="command-dropdown" />,
}));

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
    mockUploadAttachment.mockResolvedValue({ id: 'att-default' });
    mockDeleteAttachment.mockResolvedValue({ data: { success: true } });
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
    render(
      <InputToolbar {...defaultProps} isRunning={true} onStop={vi.fn()} />,
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('does not render model selector when no models', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.queryByTestId('model-selector')).toBeNull();
  });

  it('renders model selector when models are provided', () => {
    render(
      <InputToolbar
        {...defaultProps}
        models={[{ id: 'gpt-4', name: 'GPT-4' }]}
      />,
    );
    expect(screen.getByTestId('model-selector')).toBeInTheDocument();
  });

  it('renders textarea with placeholder', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined();
  });

  it('renders without crashing when isRunning=true', () => {
    render(
      <InputToolbar {...defaultProps} isRunning={true} onStop={vi.fn()} />,
    );
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined();
  });

  it('renders file attach component', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.getByTestId('file-attach')).toBeInTheDocument();
  });

  it('calls mockComposerSubmit when send button clicked with content', () => {
    setMockComposerHasContent(true);
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
    setMockComposerHasContent(false);
    render(<InputToolbar {...defaultProps} />);
    const sendBtn = screen.getByText('home.send').closest('button');
    expect(sendBtn).toBeDisabled();
  });

  it('send button is enabled when hasContent is true', () => {
    setMockComposerHasContent(true);
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
    act(() => {
      ref.current?.addFiles([new File(['a'], 'a.txt')]);
    });
    act(() => {
      ref.current?.addFiles([new File(['b'], 'b.txt')]);
    });
  });

  it('triggers toast when more than 5 files attached', () => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    const files = Array.from(
      { length: 6 },
      (_, i) => new File([`content${i}`], `file${i}.txt`),
    );
    act(() => {
      ref.current?.addFiles(files);
    });
    expect(mockToast).toHaveBeenCalled();
  });

  it('executes local command via palette on Enter', () => {
    const onExecuteCommand = vi.fn();
    paletteMock.openValue = true;
    paletteMock.filtered.push({ id: 'c1', label: 'Cmd', source: 'local' });
    paletteMock.handleKeyDown.mockReturnValue(true);
    render(
      <InputToolbar {...defaultProps} onExecuteCommand={onExecuteCommand} />,
    );
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), {
      key: 'Enter',
      shiftKey: false,
    });
    expect(paletteMock.close).toHaveBeenCalled();
    expect(onExecuteCommand).toHaveBeenCalledWith('c1');
  });

  it('inserts agent command replacement when palette handled Enter', () => {
    paletteMock.openValue = true;
    paletteMock.filtered.push({ id: 'c2', label: 'Cmd2', source: 'agent' });
    paletteMock.handleKeyDown.mockReturnValue(true);
    paletteMock.selectCommand.mockReturnValue('/Cmd2 ');
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), {
      key: 'Enter',
      shiftKey: false,
    });
    expect(paletteMock.selectCommand).toHaveBeenCalledWith(0);
    expect(mockComposerSetValue).toHaveBeenCalledWith('/Cmd2 ');
  });

  it('does not select command on Shift+Enter when palette open', () => {
    paletteMock.openValue = true;
    paletteMock.handleKeyDown.mockReturnValue(true);
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), {
      key: 'Enter',
      shiftKey: true,
    });
    expect(paletteMock.selectCommand).not.toHaveBeenCalled();
  });

  it('falls through to composer when palette does not handle key', () => {
    paletteMock.handleKeyDown.mockReturnValue(false);
    render(<InputToolbar {...defaultProps} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Type a message...'), {
      key: 'Enter',
      shiftKey: false,
    });
    expect(mockComposerHandleKeyDown).toHaveBeenCalled();
  });

  it('shows fileTooLarge and fileTypeDenied toasts on rejections', () => {
    render(<InputToolbar {...defaultProps} />);
    fireEvent.click(screen.getByTestId('file-attach'));
    expect(mockToast).toHaveBeenCalledWith('home.fileTooLarge', 'error');
    expect(mockToast).toHaveBeenCalledWith('home.fileTypeDenied', 'error');
  });

  it('uploads file on select and marks it done with attachment id', async () => {
    mockUploadAttachment.mockResolvedValue({ id: 'att-9' });
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], 'a.txt')]);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockUploadAttachment).toHaveBeenCalled();
    expect(screen.getByText('a.txt')).toBeInTheDocument();
  });

  it('shows failure state when upload fails', async () => {
    mockUploadAttachment.mockRejectedValue(new Error('network'));
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], 'a.txt')]);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText('attachment.failed')).toBeInTheDocument();
  });

  it('deletes server file when removing an uploaded attachment', async () => {
    mockUploadAttachment.mockResolvedValue({ id: 'att-9' });
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], 'a.txt')]);
    });
    await act(async () => {
      await Promise.resolve();
    });
    fireEvent.click(screen.getByRole('button', { name: /Remove a.txt/i }));
    expect(mockDeleteAttachment).toHaveBeenCalledWith('att-9');
  });
});

describe('InputToolbar attachment bar & preview', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUploadAttachment.mockResolvedValue({ id: 'att-1' });
    mockDeleteAttachment.mockResolvedValue({});
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no network')));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const addDoneFile = async (name = 'a.txt') => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], name)]);
    });
    await act(async () => {
      await Promise.resolve();
    });
  };

  it('renders attachment bar above the textarea', async () => {
    await addDoneFile();
    const textarea = screen.getByPlaceholderText('Type a message...');
    const bar = screen.getByTestId('attach-bar');
    expect(bar).toBeInTheDocument();
    expect(
      bar.compareDocumentPosition(textarea) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('does not render attachment bar when no files', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.queryByTestId('attach-bar')).toBeNull();
  });

  it('opens preview modal when attachment name clicked', async () => {
    await addDoneFile();
    fireEvent.click(screen.getByRole('button', { name: 'Preview a.txt' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('closes preview modal via close button', async () => {
    await addDoneFile();
    fireEvent.click(screen.getByRole('button', { name: 'Preview a.txt' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
