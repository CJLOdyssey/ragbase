import type { ReactNode } from 'react';
import { listModels } from '../../../api/client/models';
import { getSessionDetail, listSessions } from '../../../api/client/sessions';
import { submitRequirement } from '../../../stores/chatActions';
import { useChatStore } from '../../../stores/chatStore';
import { TestProviders } from '../../../test/setup';
import { useHomeState } from '../useHomeState';
import { act, renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

vi.mock('../../../api/client/sessions', () => ({
  listSessions: vi.fn(),
  getSessionDetail: vi.fn(),
}));

vi.mock('../../../api/client/models', () => ({
  listModels: vi.fn(),
}));

vi.mock('../../../stores/chatActions', () => ({
  submitRequirement: vi.fn(),
  retry: vi.fn(),
}));

const RUN = {
  id: 'r1',
  session_id: 'c1',
  requirement: '什么是 RAG',
  pm_document: '',
  code: '',
  review: '',
  approved: false,
  status: 'completed',
  created_at: '2026-08-08T00:00:00Z',
  updated_at: '2026-08-08T00:00:00Z',
  parent_run_id: null,
  requirement_versions: null,
  messages: [
    {
      id: 'm1',
      role: 'user',
      content: '什么是 RAG',
      agent_name: '我',
      round_number: 1,
      created_at: '2026-08-08T00:00:00Z',
    },
    {
      id: 'm2',
      role: 'agent',
      content: 'RAG 是检索增强生成',
      agent_name: 'Agent',
      round_number: 1,
      created_at: '2026-08-08T00:00:00Z',
    },
  ],
};

function renderHome() {
  return renderHook(() => useHomeState(), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <TestProviders>
        <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>
      </TestProviders>
    ),
  });
}

describe('useHomeState', { tags: ['integration'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useChatStore.getState().reset();
    vi.mocked(listSessions).mockResolvedValue([]);
    vi.mocked(getSessionDetail).mockResolvedValue({ runs: [RUN] } as never);
    vi.mocked(listModels).mockResolvedValue([]);
    vi.mocked(submitRequirement).mockResolvedValue({ run_id: 'r1' } as never);
  });

  it('renders home state with empty conversations and no messages', () => {
    const { result } = renderHome();
    expect(result.current.conversations).toEqual([]);
    expect(result.current.displayMessages).toEqual([]);
    expect(result.current.hasMessages).toBe(false);
    expect(result.current.selectedModel).toBe('');
  });

  it('recovers the model and recent models from localStorage on mount', () => {
    localStorage.setItem('ragbase-selected-model', 'gpt-4');
    localStorage.setItem(
      'ragbase-recent-models',
      JSON.stringify(['gpt-4', 'claude-3']),
    );
    const { result } = renderHome();
    expect(result.current.selectedModel).toBe('gpt-4');
  });

  it('handleModelChange persists the model and broadcasts the event', () => {
    const { result } = renderHome();
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
    act(() => result.current.setSelectedModel('claude-3'));
    expect(localStorage.getItem('ragbase-selected-model')).toBe('claude-3');
    expect(dispatchSpy).toHaveBeenCalled();
    expect(result.current.selectedModel).toBe('claude-3');
  });

  it('handleSend submits the text and ignores whitespace-only input', async () => {
    const { result } = renderHome();
    await act(async () => {
      await result.current.handleSend('你好');
    });
    expect(submitRequirement).toHaveBeenCalledWith(
      '你好',
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
    );

    await act(async () => {
      await result.current.handleSend('   ');
    });
    expect(submitRequirement).toHaveBeenCalledTimes(1);
  });

  it('handleSend passes uploaded attachment ids', async () => {
    const { result } = renderHome();
    await act(async () => {
      await result.current.handleSend('带附件', [
        {
          id: 'f1',
          name: 'a.pdf',
          size: 10,
          type: 'application/pdf',
          attachmentId: 'att-1',
          status: 'done',
        },
      ] as never);
    });
    expect(submitRequirement).toHaveBeenCalledWith(
      '带附件',
      undefined,
      undefined,
      undefined,
      undefined,
      ['att-1'],
      [{ id: 'att-1', filename: 'a.pdf' }],
    );
  });

  it('handleSwitchBranch loads the branch path into the store', async () => {
    const { result } = renderHome();
    act(() => {
      useChatStore.setState({ currentSessionId: 'c1' });
    });
    await act(async () => {
      await result.current.handleSwitchBranch('r1');
    });
    const messages = useChatStore.getState().messages;
    expect(messages.length).toBe(2);
    expect(useChatStore.getState().activeRunId).toBe('r1');
    expect(useChatStore.getState().currentSessionId).toBe('c1');
  });

  it('handleSwitchBranch is a no-op without a current session', async () => {
    const { result } = renderHome();
    await act(async () => {
      await result.current.handleSwitchBranch('r1');
    });
    expect(getSessionDetail).not.toHaveBeenCalled();
  });

  it('auth:logout clears model, sessions and navigates home', async () => {
    localStorage.setItem('ragbase-selected-model', 'gpt-4');
    const { result } = renderHome();
    act(() => {
      window.dispatchEvent(new Event('auth:logout'));
    });
    expect(result.current.selectedModel).toBe('');
    expect(result.current.conversations).toEqual([]);
  });

  it('loadConversation path marks persisted agent messages as thinking done', async () => {
    const { result } = renderHome();
    act(() => {
      useChatStore.setState({ currentSessionId: 'c1' });
    });
    await act(async () => {
      await result.current.handleSwitchBranch('r1');
    });
    await waitFor(() => {
      const agent = useChatStore
        .getState()
        .messages.find((m) => m.role !== 'user');
      expect(agent?.thinkingDone).toBe(true);
    });
    void result;
  });
});
