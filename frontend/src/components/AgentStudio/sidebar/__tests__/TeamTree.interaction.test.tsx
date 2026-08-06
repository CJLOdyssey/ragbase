import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock('../TeamTreeAgentItem', () => ({ default: () => <li data-testid="agent-item" /> }));

import TeamTree from '../TeamTree';
import type { Team, Agent } from '../../../../types/AgentStudio';

const mockTeam = (overrides: Partial<Team> = {}): Team => ({
  id: 't1', name: 'Team Alpha', isExpanded: false, isPinned: false, agents: [],
  ...overrides,
});

const baseProps = () => ({
  teams: [] as Team[],
  selectedAgentId: null as string | null,
  isAuthenticated: true,
  openLoginModal: vi.fn(),
  toggleTeam: vi.fn(),
  handleAddTeam: vi.fn(),
  handleAddAgent: vi.fn(),
  handleDeleteTeam: vi.fn(),
  handleDeleteAgent: vi.fn(),
  handleRenameTeam: vi.fn(),
  handleRenameAgent: vi.fn(),
  handleTogglePinTeam: vi.fn(),
  handleAgentClick: vi.fn(),
  onEditAgent: undefined as ((agent: Agent) => void) | undefined,
  onTeamChat: undefined as ((teamId: string) => void) | undefined,
});

function mockBoundingRect(el: HTMLElement, rect: DOMRectInit = {}) {
  const original = el.getBoundingClientRect;
  el.getBoundingClientRect = () =>
    ({ top: 0, bottom: 40, left: 0, right: 160, width: 160, height: 40, x: 0, y: 0, ...rect, toJSON: () => '' } as DOMRect);
  return () => {
    el.getBoundingClientRect = original;
  };
}

describe('TeamTree', { tags: ['integration'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls handleAddTeam when authenticated add button clicked', () => {
    const handleAddTeam = vi.fn();
    render(<TeamTree {...baseProps()} handleAddTeam={handleAddTeam} isAuthenticated={true} />);
    fireEvent.click(screen.getByTitle('sidebar.createTeam'));
    expect(handleAddTeam).toHaveBeenCalled();
  });

  it('calls openLoginModal when not authenticated add button clicked', () => {
    const openLoginModal = vi.fn();
    render(<TeamTree {...baseProps()} openLoginModal={openLoginModal} isAuthenticated={false} />);
    fireEvent.click(screen.getByTitle('登录后解锁功能'));
    expect(openLoginModal).toHaveBeenCalled();
  });

  it('calls toggleTeam when team header clicked', () => {
    const toggleTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} toggleTeam={toggleTeam} />);
    fireEvent.click(screen.getByText('Team Alpha'));
    expect(toggleTeam).toHaveBeenCalledWith('t1');
  });

  it('opens team menu on MoreVertical click', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('sidebar.addAgent')).toBeDefined();
    restore();
  });

  it('closes team menu when clicking same team again', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.queryByText('sidebar.addAgent')).toBeNull();
    restore();
  });

  it('switches team menu when clicking different team', () => {
    const teams = [mockTeam({ id: 't1' }), mockTeam({ id: 't2', name: 'Team Beta' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const buttons = screen.getAllByTitle('sidebar.moreOptions');
    const restore1 = mockBoundingRect(buttons[0]);
    const restore2 = mockBoundingRect(buttons[1]);
    fireEvent.click(buttons[0]);
    expect(screen.getByText('sidebar.addAgent')).toBeDefined();
    fireEvent.click(buttons[1]);
    expect(screen.getByText('sidebar.addAgent')).toBeDefined();
    restore1();
    restore2();
  });

  it('renders add agent item in team menu', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('sidebar.addAgent')).toBeDefined();
    restore();
  });

  it('renders rename item in team menu', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('workstation.rename')).toBeDefined();
    restore();
  });

  it('renders pin item in team menu when team is not pinned', () => {
    const teams = [mockTeam({ id: 't1', isPinned: false })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('sidebar.pin')).toBeDefined();
    restore();
  });

  it('renders unpin item in team menu when team is pinned', () => {
    const teams = [mockTeam({ id: 't1', isPinned: true })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('sidebar.unpin')).toBeDefined();
    restore();
  });

  it('renders delete item with danger class in team menu', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    const deleteBtn = screen.getByText('workstation.delete').closest('button');
    expect(deleteBtn?.className).toContain('color-danger');
    restore();
  });

  it('calls handleAddAgent when add agent menu item clicked', () => {
    const handleAddAgent = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleAddAgent={handleAddAgent} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('sidebar.addAgent'));
    expect(handleAddAgent).toHaveBeenCalledWith('t1');
    restore();
  });

  it('calls handleTogglePinTeam when pin menu item clicked', () => {
    const handleTogglePinTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleTogglePinTeam={handleTogglePinTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('sidebar.pin'));
    expect(handleTogglePinTeam).toHaveBeenCalledWith('t1');
    restore();
  });

  it('opens team edit mode when rename clicked', () => {
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    expect(input).toBeDefined();
    expect(input.value).toBe('Team Alpha');
    restore();
  });

  it('shows lock icons in team menu when not authenticated', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} isAuthenticated={false} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    const lockTitles = screen.getAllByTitle('登录后解锁功能');
    expect(lockTitles.length).toBeGreaterThanOrEqual(4);
    restore();
  });

  it('calls openLoginModal when unauthenticated add agent clicked', () => {
    const openLoginModal = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} isAuthenticated={false} openLoginModal={openLoginModal} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('sidebar.addAgent'));
    expect(openLoginModal).toHaveBeenCalled();
    restore();
  });

  it('calls openLoginModal when unauthenticated rename clicked', () => {
    const openLoginModal = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} isAuthenticated={false} openLoginModal={openLoginModal} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    expect(openLoginModal).toHaveBeenCalled();
    restore();
  });

  it('calls openLoginModal when unauthenticated pin clicked', () => {
    const openLoginModal = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} isAuthenticated={false} openLoginModal={openLoginModal} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('sidebar.pin'));
    expect(openLoginModal).toHaveBeenCalled();
    restore();
  });

  it('calls openLoginModal when unauthenticated delete clicked', () => {
    const openLoginModal = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} isAuthenticated={false} openLoginModal={openLoginModal} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    expect(openLoginModal).toHaveBeenCalled();
    restore();
  });

  it('renders team chat button when onTeamChat prop is provided', () => {
    const onTeamChat = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} onTeamChat={onTeamChat} />);
    const chatBtn = document.querySelector('[title="团队对话"]');
    expect(chatBtn).toBeDefined();
  });

  it('does not render team chat button when onTeamChat is undefined', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} onTeamChat={undefined} />);
    const chatBtn = document.querySelector('[title="团队对话"]');
    expect(chatBtn).toBeNull();
  });

  it('calls onTeamChat when chat button clicked', () => {
    const onTeamChat = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} onTeamChat={onTeamChat} />);
    const chatBtn = document.querySelector('[title="团队对话"]')!;
    fireEvent.click(chatBtn);
    expect(onTeamChat).toHaveBeenCalledWith('t1');
  });

  it('chat button click does not trigger toggleTeam', () => {
    const toggleTeam = vi.fn();
    const onTeamChat = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} toggleTeam={toggleTeam} onTeamChat={onTeamChat} />);
    const chatBtn = document.querySelector('[title="团队对话"]')!;
    fireEvent.click(chatBtn);
    expect(toggleTeam).not.toHaveBeenCalled();
  });

  it('closes team menu on document click', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    expect(screen.getByText('sidebar.addAgent')).toBeDefined();
    fireEvent.click(document);
    expect(screen.queryByText('sidebar.addAgent')).toBeNull();
    restore();
  });
});
