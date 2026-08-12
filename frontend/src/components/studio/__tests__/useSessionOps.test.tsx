import type { ReactNode } from 'react';
import {
  deleteSession,
  pinSession,
  renameSession,
} from '../../../api/client/sessions';
import { useSessionOps } from '../useSessionOps';
import { act, renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SessionItem } from '../../types';

vi.mock('../../../api/client/sessions', () => ({
  deleteSession: vi.fn(),
  pinSession: vi.fn(),
  renameSession: vi.fn(),
}));

const SESSION: SessionItem = {
  id: 's1',
  title: '会话一',
  kind: 'chat',
  run_count: 3,
  is_pinned: false,
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-02T00:00:00Z',
};

function makeParams() {
  const setCachedSessions = vi.fn();
  const setRestoring = vi.fn();
  const utils = renderHook(
    () =>
      useSessionOps({
        cachedSessions: [SESSION],
        setCachedSessions,
        activeConvId: null,
        setRestoring,
      }),
    {
      wrapper: ({ children }: { children: ReactNode }) => (
        <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>
      ),
    },
  );
  return { ...utils, setCachedSessions, setRestoring };
}

describe('useSessionOps', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(deleteSession).mockResolvedValue({});
    vi.mocked(renameSession).mockResolvedValue({});
    vi.mocked(pinSession).mockResolvedValue({});
  });

  it('maps cachedSessions to conversations and drops deleted ids', () => {
    const { result } = makeParams();
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0]).toMatchObject({
      id: 's1',
      title: '会话一',
      createdAt: '2026-08-01T00:00:00Z',
      isPinned: false,
      runCount: 3,
    });
  });

  it('handleSelectConversation navigates to the chat route and persists', () => {
    const { result } = makeParams();
    act(() => result.current.handleSelectConversation('s1'));
    expect(localStorage.getItem('ragbase-active-conv-id')).toBe('s1');
    act(() => result.current.handleSelectConversation(null));
    expect(localStorage.getItem('ragbase-active-conv-id')).toBeNull();
  });

  it('handleNewChat navigates home and clears restoring', () => {
    const { result, setRestoring } = makeParams();
    act(() => result.current.handleNewChat());
    expect(setRestoring).toHaveBeenCalledWith(false);
    expect(localStorage.getItem('ragbase-active-conv-id')).toBeNull();
  });

  it('handleDeleteConversation removes the row, writes cache and calls API', () => {
    const { result, setCachedSessions } = makeParams();
    act(() => result.current.handleDeleteConversation('s1'));
    expect(deleteSession).toHaveBeenCalledWith('s1');
    expect(setCachedSessions).toHaveBeenCalled();
    const updater = setCachedSessions.mock.calls[0][0];
    expect(updater([SESSION])).toEqual([]);
    expect(result.current.conversations).toEqual([]);
  });

  it('handleRenameConversation ignores empty titles', () => {
    const { result } = makeParams();
    act(() => result.current.handleRenameConversation('s1', '   '));
    expect(renameSession).not.toHaveBeenCalled();
  });

  it('handleRenameConversation applies the trimmed title and calls API', () => {
    const { result, setCachedSessions } = makeParams();
    act(() => result.current.handleRenameConversation('s1', '  新名字 '));
    expect(renameSession).toHaveBeenCalledWith('s1', '新名字');
    expect(result.current.conversations[0].title).toBe('新名字');
    const updater = setCachedSessions.mock.calls[0][0];
    expect(updater([SESSION])[0].title).toBe('新名字');
  });

  it('handlePinConversation toggles pinned state and calls API', () => {
    const { result, setCachedSessions } = makeParams();
    act(() => result.current.handlePinConversation('s1'));
    expect(pinSession).toHaveBeenCalledWith('s1', true);
    expect(result.current.conversations[0].isPinned).toBe(true);
    const updater = setCachedSessions.mock.calls[0][0];
    expect(updater([SESSION])[0].is_pinned).toBe(true);

    act(() => result.current.handlePinConversation('s1'));
    expect(pinSession).toHaveBeenLastCalledWith('s1', false);
    expect(result.current.conversations[0].isPinned).toBe(false);
  });

  it('delete/rename/pin API failures are swallowed (best-effort)', () => {
    vi.mocked(deleteSession).mockRejectedValue(new Error('net'));
    vi.mocked(renameSession).mockRejectedValue(new Error('net'));
    vi.mocked(pinSession).mockRejectedValue(new Error('net'));
    const { result } = makeParams();
    act(() => result.current.handleDeleteConversation('s1'));
    act(() => result.current.handleRenameConversation('s1', 'x'));
    act(() => result.current.handlePinConversation('s1'));
    expect(result.current.conversations).toHaveLength(0);
  });
});
