import { listPrompts } from '../../../../api/client/prompts';
import { usePickerState, type PickerItem } from '../usePickerState';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('../../../../api/client/prompts', () => ({
  listPrompts: vi.fn(),
}));

vi.mock('../../../../i18n/index', () => ({
  default: { t: (k: string) => `[${k}]` },
}));

const SYSTEM_PROMPT: PickerItem = {
  id: 'p1',
  name: 'System Prompt',
  description: 'system description',
};

const OUTPUT_PROMPT: PickerItem = {
  id: 'p2',
  name: 'Output Prompt',
  description: 'output description',
};

function makeDeps() {
  return {
    setSystemPrompt: vi.fn(),
    setOutputConstraints: vi.fn(),
    addTool: vi.fn(),
    addMcp: vi.fn(),
    addSkill: vi.fn(),
  };
}

describe('usePickerState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'p1',
        name: 'System Prompt',
        category: 'system',
        content: 'system description',
        model: null,
        status: 'active',
        version: '1',
        created_at: '2026-08-01T00:00:00Z',
      },
      {
        id: 'p2',
        name: 'Output Prompt',
        category: 'output',
        content: 'output description',
        model: null,
        status: 'active',
        version: '1',
        created_at: '2026-08-01T00:00:00Z',
      },
    ]);
  });

  it('loads system and output prompts into pickerItems on mount', async () => {
    const deps = makeDeps();
    const { result } = renderHook(() => usePickerState(deps));
    await waitFor(() => {
      expect(result.current.pickerItems.system).toHaveLength(1);
      expect(result.current.pickerItems.output).toHaveLength(1);
    });
    expect(result.current.pickerItems.system[0]).toEqual({
      ...SYSTEM_PROMPT,
      source: '[providerEdit.pickerPrompt]',
    });
    expect(result.current.pickerItems.output[0]).toEqual({
      ...OUTPUT_PROMPT,
      source: '[providerEdit.pickerOutput]',
    });
  });

  it('truncates long system prompt descriptions to 120 chars', async () => {
    const long = 'x'.repeat(200);
    vi.mocked(listPrompts).mockResolvedValue([
      {
        id: 'p1',
        name: 'Long Prompt',
        category: 'system',
        content: long,
        model: null,
        status: 'active',
        version: '1',
        created_at: '2026-08-01T00:00:00Z',
      },
    ]);
    const { result } = renderHook(() => usePickerState(makeDeps()));
    await waitFor(() =>
      expect(result.current.pickerItems.system).toHaveLength(1),
    );
    expect(result.current.pickerItems.system[0].description).toBe(
      long.slice(0, 120) + '…',
    );
  });

  it('survives listPrompts failure without crashing', async () => {
    vi.mocked(listPrompts).mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => usePickerState(makeDeps()));
    await waitFor(() => {
      expect(result.current.pickerItems).toEqual({});
    });
  });

  it('handlePickerSelect appends system description to the system prompt', () => {
    const deps = makeDeps();
    const { result } = renderHook(() => usePickerState(deps));
    act(() => result.current.handlePickerSelect('system', SYSTEM_PROMPT));
    expect(deps.setSystemPrompt).toHaveBeenCalled();
    const updater = deps.setSystemPrompt.mock.calls[0][0];
    expect(updater('')).toBe('system description');
    expect(updater('prev')).toBe('prev\n\nsystem description');
    expect(result.current.pickerTab).toBeNull();
  });

  it('handlePickerSelect appends output description with newline separator', () => {
    const deps = makeDeps();
    const { result } = renderHook(() => usePickerState(deps));
    act(() => result.current.handlePickerSelect('output', OUTPUT_PROMPT));
    const updater = deps.setOutputConstraints.mock.calls[0][0];
    expect(updater('')).toBe('output description');
    expect(updater('prev')).toBe('prev\noutput description');
  });

  it('handlePickerSelect dispatches tools/mcp/skills to their adders', () => {
    const deps = makeDeps();
    const { result } = renderHook(() => usePickerState(deps));
    act(() => result.current.handlePickerSelect('tools', SYSTEM_PROMPT));
    expect(deps.addTool).toHaveBeenCalledWith(SYSTEM_PROMPT);
    act(() => result.current.handlePickerSelect('mcp', SYSTEM_PROMPT));
    expect(deps.addMcp).toHaveBeenCalledWith(SYSTEM_PROMPT);
    act(() => result.current.handlePickerSelect('skills', SYSTEM_PROMPT));
    expect(deps.addSkill).toHaveBeenCalledWith(SYSTEM_PROMPT);
    expect(result.current.pickerTab).toBeNull();
  });

  it('unknown tab does not call any adder', () => {
    const deps = makeDeps();
    const { result } = renderHook(() => usePickerState(deps));
    act(() => result.current.handlePickerSelect('unknown', SYSTEM_PROMPT));
    expect(deps.setSystemPrompt).not.toHaveBeenCalled();
    expect(deps.setOutputConstraints).not.toHaveBeenCalled();
    expect(deps.addTool).not.toHaveBeenCalled();
  });
});
