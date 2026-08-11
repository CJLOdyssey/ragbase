import { TestProviders } from '../../../../test/setup';
import type { Conversation } from '../../../../types/studio';
import ConversationsList from '../ConversationsList';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const baseProps = {
  activeConvId: null as string | null,
  selectedAgentId: null as string | null,
  onSelect: vi.fn(),
  onDelete: vi.fn(),
};

function renderList(conversations: Conversation[]) {
  return render(
    <TestProviders>
      <ConversationsList {...baseProps} conversations={conversations} />
    </TestProviders>,
  );
}

describe('ConversationsList reply status', () => {
  it('shows replied when session has runs (runCount > 0, no messages loaded)', () => {
    // 会话列表来自后端 sessions：messages 恒为空，回复状态由 run_count 判定。
    const conv: Conversation = {
      id: 'c1',
      title: '会话A',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      runCount: 3,
    };
    renderList([conv]);
    expect(screen.getByText(/已回复/)).toBeInTheDocument();
    expect(screen.queryByText(/等待回复/)).not.toBeInTheDocument();
  });

  it('shows pending when session has no runs and no messages', () => {
    const conv: Conversation = {
      id: 'c2',
      title: '会话B',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      runCount: 0,
    };
    renderList([conv]);
    expect(screen.getByText(/等待回复/)).toBeInTheDocument();
  });

  it('shows replied when messages contain agent reply', () => {
    const conv: Conversation = {
      id: 'c3',
      title: '会话C',
      messages: [
        { id: 'm1', role: 'user', content: 'q' },
        { id: 'm2', role: 'pm', content: 'a' },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    renderList([conv]);
    expect(screen.getByText(/已回复/)).toBeInTheDocument();
  });
});
