import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VirtuosoMockContext } from 'react-virtuoso';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: 'zh' } }),
}));

import ConversationsList from '../ConversationsList';
import type { Conversation, Agent } from '../../../../types/AgentStudio';
import type * as React from 'react';

function makeConv(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: 'c1',
    title: 'Chat 1',
    updatedAt: new Date().toISOString(),
    messages: [],
    ...overrides,
  } as Conversation;
}

const now = new Date();
const dayMs = 24 * 60 * 60 * 1000;

describe('ConversationsList', { tags: ['integration'] }, () => {
  const baseProps = {
    conversations: [] as Conversation[],
    activeConvId: null as string | null,
    selectedAgentId: null as string | null,
    onSelect: vi.fn(),
    onDelete: vi.fn(),
  };

  function renderWithVirtuoso(conversations: Conversation[], props: Partial<React.ComponentProps<typeof ConversationsList>> = {}) {
    return render(
      <VirtuosoMockContext.Provider value={{ viewportHeight: 300, itemHeight: 50 }}>
        <ConversationsList
          {...baseProps}
          conversations={conversations}
          {...props}
        />
      </VirtuosoMockContext.Provider>
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when no conversations', () => {
    const { container } = renderWithVirtuoso([]);
    expect(container.innerHTML).toBe('');
  });

  it('renders conversation items', () => {
    const conversations = [makeConv()];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('Chat 1');
  });

  it('renders multiple conversations', () => {
    const conversations = [
      makeConv({ id: 'c1', title: 'Chat 1' }),
      makeConv({ id: 'c2', title: 'Chat 2' }),
    ];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('Chat 1');
    expect(container.textContent).toContain('Chat 2');
  });

  it('renders time group labels', () => {
    const conversations = [makeConv()];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.today');
  });

  it('renders yesterday group', () => {
    const conversations = [makeConv({ updatedAt: new Date(now.getTime() - dayMs).toISOString() })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.yesterday');
  });

  it('renders threeDays group', () => {
    const conversations = [makeConv({ updatedAt: new Date(now.getTime() - 2 * dayMs).toISOString() })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.threeDays');
  });

  it('renders sevenDays group', () => {
    const conversations = [makeConv({ updatedAt: new Date(now.getTime() - 5 * dayMs).toISOString() })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.sevenDays');
  });

  it('renders month group', () => {
    const conversations = [makeConv({ updatedAt: new Date(now.getTime() - 15 * dayMs).toISOString() })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.month');
  });

  it('renders older group', () => {
    const conversations = [makeConv({ updatedAt: new Date(now.getTime() - 60 * dayMs).toISOString() })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.older');
  });

  it('marks active conversation', () => {
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { activeConvId: 'c1' });
    const item = document.querySelector('[aria-selected="true"]');
    expect(item).toBeInTheDocument();
  });

  it('does not mark inactive conversation', () => {
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { activeConvId: 'c2' });
    const item = document.querySelector('[aria-selected="true"]');
    expect(item).toBeNull();
  });

  it('calls onSelect when conversation clicked', () => {
    const onSelect = vi.fn();
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { onSelect });
    const item = document.querySelector('[role="button"]');
    if (item) fireEvent.click(item);
    expect(onSelect).toHaveBeenCalledWith(conversations[0]);
  });

  it('calls onSelect on Enter key', () => {
    const onSelect = vi.fn();
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { onSelect });
    const item = document.querySelector('[role="button"]');
    if (item) fireEvent.keyDown(item, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalled();
  });

  it('calls onSelect on Space key', () => {
    const onSelect = vi.fn();
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { onSelect });
    const item = document.querySelector('[role="button"]');
    if (item) fireEvent.keyDown(item, { key: ' ' });
    expect(onSelect).toHaveBeenCalled();
  });

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn();
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { onDelete });
    fireEvent.click(screen.getByRole('button', { name: '更多' }));
    fireEvent.click(screen.getByText('删除'));
    expect(onDelete).toHaveBeenCalledWith('c1');
  });

  it('delete click does not trigger onSelect', () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const conversations = [makeConv({ id: 'c1' })];
    renderWithVirtuoso(conversations, { onSelect, onDelete });
    fireEvent.click(screen.getByRole('button', { name: '更多' }));
    fireEvent.click(screen.getByText('删除'));
    expect(onSelect).not.toHaveBeenCalled();
    expect(onDelete).toHaveBeenCalled();
  });

  it('has accessible delete button', () => {
    const conversations = [makeConv()];
    renderWithVirtuoso(conversations);
    fireEvent.click(screen.getByRole('button', { name: '更多' }));
    expect(screen.getByText('删除')).toBeInTheDocument();
  });

  it('has accessible conv item with tabIndex', () => {
    const conversations = [makeConv()];
    renderWithVirtuoso(conversations);
    const item = document.querySelector('[role="button"]');
    expect(item?.getAttribute('tabindex')).toBe('0');
  });

  it('renders team icon for team conversations', () => {
    const conversations = [makeConv({ teamId: 'team-1', teamName: 'Dev Team' })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('Dev Team');
  });

  it('shows replied status when agent messages exist', () => {
    const conversations = [makeConv({ messages: [{ id: 'm1', role: 'agent', content: 'hi' }] })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('sidebar.replied');
  });

  it('truncates long titles', () => {
    const longTitle = '这是一段很长的对话标题需要被截断显示' + 'x'.repeat(50);
    const conversations = [makeConv({ title: longTitle })];
    const { container } = renderWithVirtuoso(conversations);
    expect(container.textContent).toContain('...');
  });

  it('renders without Virtuoso context gracefully', () => {
    // Without VirtuosoMockContext, Virtuoso might still render
    const { container } = render(<ConversationsList {...baseProps} conversations={[makeConv()]} />);
    expect(container).toBeDefined();
  });

  it('does not crash when agents prop matches conversation', () => {
    const convAgent = { id: 'a1', name: 'Bot', icon: 'Bot', role: 'assistant', color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe' };
    const conversations = [makeConv({ agentId: 'a1' })] as Conversation[];
    render(
      <VirtuosoMockContext.Provider value={{ viewportHeight: 300, itemHeight: 50 }}>
        <ConversationsList
          {...baseProps}
          conversations={conversations}
          agents={[convAgent as unknown as Agent]}
        />
      </VirtuosoMockContext.Provider>
    );
    expect(true).toBe(true);
  });
});
