import { useChatStore } from '../../../stores/chatStore';
import { TestProviders } from '../../../test/setup';
import type { Message } from '../../../types/studio';
import MessagesPanel from '../MessagesPanel';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

const chatActionsMock = vi.hoisted(() => ({
  continueGeneration: vi.fn(),
  editAndRegenerate: vi.fn(),
  regenerateMessage: vi.fn(),
}));

vi.mock('../../../stores/chatActions', () => chatActionsMock);

const USER_MSG: Message = {
  id: 'u1',
  role: 'user',
  content: '我的问题',
};
const AGENT_MSG: Message = {
  id: 'a1',
  role: 'agent',
  content: '我的回答',
  thinking: '推理',
  thinkingDone: true,
};

const baseProps = {
  showAgentChat: true,
  hasMessages: true,
  allAgents: [] as never[],
  displayMessages: [USER_MSG, AGENT_MSG] as Message[],
  messagesEndRef: { current: null },
  onSwitchBranch: vi.fn(),
};

function renderPanel(extra: Record<string, unknown> = {}) {
  return render(
    <TestProviders>
      <MessagesPanel {...baseProps} {...extra} />
    </TestProviders>,
  );
}

describe('MessagesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.setState({
      interruptedMessageId: null,
      continuingId: null,
      messages: [],
    });
  });

  it('renders user and agent messages', () => {
    renderPanel();
    expect(screen.getByText('我的问题')).toBeInTheDocument();
    expect(screen.getByText('我的回答')).toBeInTheDocument();
  });

  it('renders messages via hasMessages branch too', () => {
    renderPanel({ showAgentChat: false });
    expect(screen.getByText('我的问题')).toBeInTheDocument();
  });

  it('renders nothing when no messages', () => {
    renderPanel({
      showAgentChat: false,
      hasMessages: false,
      displayMessages: [],
    });
    expect(screen.queryByText('我的问题')).not.toBeInTheDocument();
  });

  it('shows continue button for interrupted message and fires onContinue', () => {
    useChatStore.setState({ interruptedMessageId: 'a1' });
    renderPanel();
    const btn = screen.getByRole('button', { name: 'teamMessage.continue' });
    fireEvent.click(btn);
    expect(chatActionsMock.continueGeneration).toHaveBeenCalled();
  });

  it('regenerates via regenerate button', () => {
    renderPanel();
    fireEvent.click(
      screen.getByRole('button', { name: 'teamMessage.regenerate' }),
    );
    expect(chatActionsMock.regenerateMessage).toHaveBeenCalledWith(1);
  });

  it('records thumbs feedback through the store', () => {
    useChatStore.setState({
      messages: [
        { id: 'a1', role: 'agent', content: '我的回答', thumbs: null },
      ],
    });
    renderPanel();
    fireEvent.click(
      screen.getByRole('button', { name: 'teamMessage.thumbsUp' }),
    );
    const { messages } = useChatStore.getState();
    const agent = messages.find((m) => m.id === 'a1');
    expect(agent?.thumbs).toBe('up');
  });

  it('switches answer version branch via version pager', () => {
    const onSwitchBranch = vi.fn();
    const withVersions: Message[] = [
      {
        id: 'a2',
        role: 'agent',
        content: 'v1 回答',
        answerVersions: ['v1 回答', 'v2 回答'],
        answerRunIds: ['r1', 'r2'],
        currentAnswerVersion: 0,
      },
    ];
    useChatStore.setState({
      messages: [
        {
          id: 'a2',
          role: 'agent',
          content: 'v1 回答',
          answerVersions: ['v1 回答', 'v2 回答'],
          answerRunIds: ['r1', 'r2'],
          currentAnswerVersion: 0,
        },
      ],
    });
    renderPanel({ displayMessages: withVersions, onSwitchBranch });
    fireEvent.click(
      screen.getByRole('button', { name: 'Next answer version' }),
    );
    expect(onSwitchBranch).toHaveBeenCalledWith('r2');
  });

  it('switches user version branch via version pager', () => {
    const onSwitchBranch = vi.fn();
    const withVersions: Message[] = [
      {
        id: 'u2',
        role: 'user',
        content: '旧问题',
        userVersions: ['旧问题', '新问题'],
        versionRunIds: ['r1', 'r2'],
        currentUserVersion: 0,
      },
    ];
    useChatStore.setState({
      messages: [
        {
          id: 'u2',
          role: 'user',
          content: '旧问题',
          userVersions: ['旧问题', '新问题'],
          versionRunIds: ['r1', 'r2'],
          currentUserVersion: 0,
        },
      ],
    });
    renderPanel({ displayMessages: withVersions, onSwitchBranch });
    fireEvent.click(screen.getByRole('button', { name: 'Next user version' }));
    expect(onSwitchBranch).toHaveBeenCalledWith('r2');
  });

  it('edits a user message via the edit flow', () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: '改后问题' },
    });
    fireEvent.click(screen.getByText('common.send'));
    expect(chatActionsMock.editAndRegenerate).toHaveBeenCalledWith(
      'u1',
      '改后问题',
    );
  });

  it('flushes store state without leaking across tests', () => {
    act(() => {});
    expect(useChatStore.getState().messages).toEqual([]);
  });
});
