// Shared mock fns for InputToolbar tests. vi.mock declarations live in the
// test file (hoisted above imports); this module only exports the mock fns
// the factories and test bodies reference.
import { vi } from 'vitest';

export const mockComposerSetValue = vi.fn();
export const mockComposerSubmit = vi.fn();
export const mockComposerHandleKeyDown = vi.fn();

let mockComposerHasContent = false;
export const setMockComposerHasContent = (v: boolean): void => {
  mockComposerHasContent = v;
};
export const getComposerHasContent = (): boolean => mockComposerHasContent;

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

export const mockToast = vi.fn();

export const mockUploadAttachment = vi.fn();
export const mockDeleteAttachment = vi.fn();
