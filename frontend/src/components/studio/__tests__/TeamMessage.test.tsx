import type { Message } from '../../../types/studio';
import TeamMessage from '../TeamMessage';
import { fireEvent, render, screen } from '@testing-library/react';
import { Bot } from 'lucide-react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

const AGENT = {
  id: 'pm',
  name: 'PM',
  role: 'assistant',
  icon: Bot,
  color: 'text-blue-500',
  bg: 'bg-blue-100',
  border: 'border-blue-200',
};

function makeMsg(overrides: Partial<Message>): Message {
  return {
    id: 'm1',
    role: 'agent',
    content: '答案内容',
    ...overrides,
  };
}

const noop = () => {};

function renderTeam(msg: Message, extra: Record<string, unknown> = {}) {
  return render(
    <TeamMessage
      msg={msg}
      allAgents={[AGENT]}
      onEditMessage={noop}
      onRegenerate={noop}
      onContinue={noop}
      onSwitchUserVersion={noop}
      onSwitchAnswer={noop}
      onThumbsFeedback={noop}
      {...extra}
    />,
  );
}

describe('TeamMessage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('delegates user-role messages to UserMessage', () => {
    renderTeam(makeMsg({ role: 'user', content: '我的问题' }));
    expect(screen.getByText('我的问题')).toBeInTheDocument();
  });

  it('renders agent markdown content and thinking section', () => {
    renderTeam(
      makeMsg({
        thinking: '推理过程',
        thinkingDone: true,
        content: '**加粗**内容',
      }),
    );
    expect(
      screen.getByText('teamMessage.thinkingComplete'),
    ).toBeInTheDocument();
    expect(screen.getByText('加粗')).toBeInTheDocument();
    expect(screen.getByText('内容')).toBeInTheDocument();
  });

  it('shows unknown-agent fallback name in typing indicator', () => {
    renderTeam(makeMsg({ agentId: 'ghost', isTyping: true }));
    expect(screen.getByText('agent.thinking')).toBeInTheDocument();
  });

  it('renders isTyping state with spinner text', () => {
    renderTeam(makeMsg({ isTyping: true }));
    expect(screen.getByText('agent.thinking')).toBeInTheDocument();
  });

  it('renders plan card and toggles its expansion', () => {
    renderTeam(
      makeMsg({
        plan: [
          { step: '收集需求', status: 'completed' as const },
          { step: '设计架构', status: 'running' as const },
        ],
      }),
    );
    expect(screen.getByText('收集需求')).toBeInTheDocument();
    expect(screen.getByText('设计架构')).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: /teamMessage.executeTask/ }),
    );
    expect(screen.queryByText('收集需求')).not.toBeInTheDocument();
  });

  it('renders action label without plan', () => {
    renderTeam(makeMsg({ action: { type: 'tool', label: '调用搜索' } }));
    expect(screen.getByText('调用搜索')).toBeInTheDocument();
  });

  it('renders and collapses sources block', () => {
    renderTeam(
      makeMsg({
        sources: [
          {
            asset_id: 'a1',
            asset_name: 'doc.md',
            text: '来源摘要',
            similarity: 0.87,
          },
        ],
      }),
    );
    expect(screen.getByText('来源摘要')).toBeInTheDocument();
    fireEvent.click(screen.getByText('teamMessage.sources'));
    expect(screen.queryByText('来源摘要')).not.toBeInTheDocument();
  });

  it('omits sources block when no sources', () => {
    renderTeam(makeMsg({}));
    expect(screen.queryByText('teamMessage.sources')).not.toBeInTheDocument();
  });

  it('shows interrupted banner and continue button when showContinue', () => {
    const onContinue = vi.fn();
    renderTeam(makeMsg({ thinkingDone: true }), {
      showContinue: true,
      onContinue,
    });
    expect(screen.getByText('teamMessage.interrupted')).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: 'teamMessage.continue' });
    fireEvent.click(btn);
    expect(onContinue).toHaveBeenCalled();
  });

  it('disables continue button while isContinuing', () => {
    renderTeam(makeMsg({}), { showContinue: true, isContinuing: true });
    const btn = screen.getByRole('button', { name: 'teamMessage.continuing' });
    expect(btn).toBeDisabled();
  });

  it('regenerate button triggers onRegenerate', () => {
    const onRegenerate = vi.fn();
    renderTeam(makeMsg({}), { onRegenerate });
    fireEvent.click(
      screen.getByRole('button', { name: 'teamMessage.regenerate' }),
    );
    expect(onRegenerate).toHaveBeenCalledWith('m1');
  });

  it('thumbs up/down toggle feedback', () => {
    const onThumbsFeedback = vi.fn();
    renderTeam(makeMsg({}), { onThumbsFeedback });
    fireEvent.click(
      screen.getByRole('button', { name: 'teamMessage.thumbsUp' }),
    );
    expect(onThumbsFeedback).toHaveBeenCalledWith('m1', 'up');
    fireEvent.click(
      screen.getByRole('button', { name: 'teamMessage.thumbsDown' }),
    );
    expect(onThumbsFeedback).toHaveBeenCalledWith('m1', 'down');
  });

  it('active thumbs button becomes remove-feedback', () => {
    renderTeam(makeMsg({ thumbsFeedback: 'up' }));
    const btn = screen.getByRole('button', {
      name: 'teamMessage.removeFeedback',
    });
    fireEvent.click(btn);
    expect(btn).toBeTruthy();
  });

  it('renders version pager when multiple answer versions', () => {
    const onSwitchAnswer = vi.fn();
    renderTeam(
      makeMsg({ answerVersions: ['v1', 'v2'], currentAnswerVersion: 0 }),
      { onSwitchAnswer },
    );
    expect(screen.getByText('1/2')).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: 'Next answer version' }),
    );
    expect(onSwitchAnswer).toHaveBeenCalledWith('m1', 'next');
  });

  it('does not render version pager with single version', () => {
    renderTeam(makeMsg({ answerVersions: ['v1'] }));
    expect(screen.queryByText('1/1')).not.toBeInTheDocument();
  });
});
