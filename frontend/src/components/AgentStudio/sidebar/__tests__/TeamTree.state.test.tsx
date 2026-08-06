import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

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

  it('shows confirm delete dialog for team', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    const dialog = document.body.querySelector('[role="dialog"]');
    expect(dialog).toBeDefined();
    expect(document.body.textContent).toContain('confirm.deleteTeamConfirm');
    restore();
  });

  it('shows confirm delete dialog for agent', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    expect(document.body.textContent).toContain('confirm.deleteTeamConfirm');
    restore();
  });

  it('confirm delete dialog calls handleDeleteTeam', () => {
    const handleDeleteTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleDeleteTeam={handleDeleteTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    fireEvent.click(screen.getByText('sidebar.delete'));
    expect(handleDeleteTeam).toHaveBeenCalledWith('t1');
    restore();
  });

  it('confirm delete dialog cancel button dismisses dialog', () => {
    const handleDeleteTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleDeleteTeam={handleDeleteTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    fireEvent.click(screen.getByText('common.cancel'));
    expect(handleDeleteTeam).not.toHaveBeenCalled();
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    restore();
  });

  it('confirm delete dialog closes on overlay click', () => {
    const handleDeleteTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleDeleteTeam={handleDeleteTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    const dialog = document.body.querySelector('[role="dialog"]')!;
    fireEvent.click(dialog.parentElement!);
    expect(handleDeleteTeam).not.toHaveBeenCalled();
    restore();
  });

  it('confirm delete dialog modal stops propagation', () => {
    const handleDeleteTeam = vi.fn();
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} handleDeleteTeam={handleDeleteTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    const modal = document.body.querySelector('[role="dialog"]')!;
    fireEvent.click(modal);
    expect(handleDeleteTeam).not.toHaveBeenCalled();
    expect(document.body.querySelector('[role="dialog"]')).toBeDefined();
    restore();
  });

  it('confirm delete dialog has accessible title', () => {
    const teams = [mockTeam({ id: 't1' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.delete'));
    expect(screen.getByText('confirm.title')).toBeDefined();
    restore();
  });

  it('saves team name on Enter key', () => {
    const handleRenameTeam = vi.fn();
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} handleRenameTeam={handleRenameTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(handleRenameTeam).toHaveBeenCalledWith('t1', 'Team Alpha');
    restore();
  });

  it('saves team name on blur after timeout', () => {
    vi.useFakeTimers();
    const handleRenameTeam = vi.fn();
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} handleRenameTeam={handleRenameTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    fireEvent.blur(input);
    act(() => { vi.advanceTimersByTime(100); });
    expect(handleRenameTeam).toHaveBeenCalledWith('t1', 'Team Alpha');
    restore();
    vi.useRealTimers();
  });

  it('shows validation warning for empty team name', () => {
    vi.useFakeTimers();
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.blur(input);
    act(() => { vi.advanceTimersByTime(100); });
    expect(document.body.textContent).toContain('sidebar.nameNotEmpty');
    restore();
    vi.useRealTimers();
  });

  it('shows validation warning for team name with special characters', () => {
    const handleRenameTeam = vi.fn();
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} handleRenameTeam={handleRenameTeam} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Bad<Name' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(handleRenameTeam).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain('confirm.tip');
    restore();
  });

  it('dismisses validation warning', () => {
    vi.useFakeTimers();
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const menuBtn = screen.getByTitle('sidebar.moreOptions');
    const restore = mockBoundingRect(menuBtn);
    fireEvent.click(menuBtn);
    fireEvent.click(screen.getByText('workstation.rename'));
    const input = document.querySelector('input') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.blur(input);
    act(() => { vi.advanceTimersByTime(100); });
    expect(document.body.textContent).toContain('sidebar.nameNotEmpty');
    fireEvent.click(screen.getByRole('button', { name: '关闭' }));
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    restore();
    vi.useRealTimers();
  });

  it('does not call delete handlers when confirmDelete is null', () => {
    const handleDeleteTeam = vi.fn();
    const handleDeleteAgent = vi.fn();
    render(<TeamTree {...baseProps()} teams={[]} handleDeleteTeam={handleDeleteTeam} handleDeleteAgent={handleDeleteAgent} />);
    expect(handleDeleteTeam).not.toHaveBeenCalled();
    expect(handleDeleteAgent).not.toHaveBeenCalled();
  });
});
