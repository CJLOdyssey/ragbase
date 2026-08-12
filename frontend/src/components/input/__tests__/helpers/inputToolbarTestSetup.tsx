import { vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

export const mockComposerSetValue = vi.fn();
export const mockComposerSubmit = vi.fn();
export const mockComposerHandleKeyDown = vi.fn();

let mockComposerHasContent = false;
export const setMockComposerHasContent = (v: boolean): void => {
  mockComposerHasContent = v;
};

vi.mock('@/hooks/useMessageComposer', () => ({
  useMessageComposer: () => ({
    value: '',
    setValue: mockComposerSetValue,
    submit: mockComposerSubmit,
    handleKeyDown: mockComposerHandleKeyDown,
    get hasContent() {
      return mockComposerHasContent;
    },
    charCount: 0,
    maxLength: 2000,
  }),
}));

export const paletteMock = {
  filtered: [] as Array<{ id: string; label: string; source: string }>,
  updateFromValue: vi.fn(),
  handleKeyDown: vi.fn(() => false),
  selectCommand: vi.fn(),
  close: vi.fn(),
  _open: false,
  set openValue(v: boolean) {
    this._open = v;
  },
  get openValue() {
    return this._open;
  },
};

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

export const mockToast = vi.fn();

vi.mock('@/utils/useToast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

export const mockUploadAttachment = vi.fn();
export const mockDeleteAttachment = vi.fn();

vi.mock('@/api/client/attachments', () => ({
  uploadAttachment: mockUploadAttachment,
  deleteAttachment: mockDeleteAttachment,
}));

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
