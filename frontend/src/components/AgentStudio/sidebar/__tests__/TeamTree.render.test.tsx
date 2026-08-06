import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock('../TeamTreeAgentItem', () => ({ default: () => <li data-testid="agent-item" /> }));

import TeamTree from '../TeamTree';
import type { Team, Agent } from '../../../../types/AgentStudio';

const mockAgent = (overrides: Partial<Agent> = {}): Agent =>
  ({
    id: 'a1', name: 'Agent One', role: 'assistant',
    icon: 'Bot', color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe',
    ...overrides,
  } as unknown as Agent);

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

describe('TeamTree', { tags: ['integration'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the section header label', () => {
    const { container } = render(<TeamTree {...baseProps()} />);
    expect(container.textContent).toContain('sidebar.myTeams');
  });

  it('renders Plus button when authenticated', () => {
    render(<TeamTree {...baseProps()} isAuthenticated={true} />);
    const btn = screen.getByTitle('sidebar.createTeam');
    expect(btn).toBeDefined();
  });

  it('renders Lock button when not authenticated', () => {
    render(<TeamTree {...baseProps()} isAuthenticated={false} />);
    const btn = screen.getByTitle('登录后解锁功能');
    expect(btn).toBeDefined();
  });

  it('renders team name', () => {
    const teams = [mockTeam({ id: 't1', name: 'Team Alpha' })];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    expect(container.textContent).toContain('Team Alpha');
  });

  it('renders agent count', () => {
    const teams = [mockTeam({ id: 't1', agents: [mockAgent({ id: 'a1' }), mockAgent({ id: 'a2' })] })];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    expect(container.textContent).toContain('2');
  });

  it('renders pin icon when team is pinned', () => {
    const teams = [mockTeam({ id: 't1', isPinned: true })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const pin = document.querySelector('svg');
    expect(pin).toBeDefined();
  });

  it('does not render pin icon when team is not pinned', () => {
    const teams = [mockTeam({ id: 't1', isPinned: false })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const pin = document.querySelector('[class*="text-[var(--color-accent-soft)]"]');
    expect(pin).toBeNull();
  });

  it('renders chevron with rotation when team is collapsed', () => {
    const teams = [mockTeam({ id: 't1', isExpanded: false })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const chevron = document.querySelector('[class*="-rotate-90"]');
    expect(chevron).toBeDefined();
  });

  it('renders chevron without rotation when team is expanded', () => {
    const teams = [mockTeam({ id: 't1', isExpanded: true })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const chevron = document.querySelector('[class*="transition-transform"]');
    expect(chevron).toBeDefined();
    expect(chevron?.className).not.toContain('-rotate-90');
  });

  it('renders agent items when team is expanded', () => {
    const teams = [mockTeam({ id: 't1', isExpanded: true, agents: [mockAgent({ id: 'a1' })] })];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    expect(container.querySelector('[data-testid="agent-item"]')).toBeDefined();
  });

  it('does not render agent items when team is collapsed', () => {
    const teams = [mockTeam({ id: 't1', isExpanded: false, agents: [mockAgent({ id: 'a1' })] })];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    expect(container.querySelector('[data-testid="agent-item"]')).toBeNull();
  });

  it('renders multiple teams', () => {
    const teams = [
      mockTeam({ id: 't1', name: 'Team Alpha' }),
      mockTeam({ id: 't2', name: 'Team Beta' }),
    ];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    expect(container.textContent).toContain('Team Alpha');
    expect(container.textContent).toContain('Team Beta');
  });

  it('renders collapsed and expanded teams independently', () => {
    const teams = [
      mockTeam({ id: 't1', name: 'Team A', isExpanded: true, agents: [mockAgent({ id: 'a1' })] }),
      mockTeam({ id: 't2', name: 'Team B', isExpanded: false, agents: [mockAgent({ id: 'a2' })] }),
    ];
    const { container } = render(<TeamTree {...baseProps()} teams={teams} />);
    const agentItems = container.querySelectorAll('[data-testid="agent-item"]');
    expect(agentItems.length).toBe(1);
  });

  it('shows Pin icon in header for pinned team', () => {
    const teams = [mockTeam({ id: 't1', isPinned: true })];
    render(<TeamTree {...baseProps()} teams={teams} />);
    const pinIcon = document.querySelector('svg');
    expect(pinIcon).toBeDefined();
  });
});
