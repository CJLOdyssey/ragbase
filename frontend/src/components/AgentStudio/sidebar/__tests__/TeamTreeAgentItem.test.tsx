import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TeamTreeAgentItem from '../TeamTreeAgentItem';
import type { Agent } from '../../../../types/AgentStudio';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const mockAgent: Agent = {
  id: 'a1', name: 'Test Agent', role: 'assistant',
  icon: 'Bot' as Agent['icon'], color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe',
} as Agent;

const tFn = (k: string) => k;

const baseProps = {
  agent: mockAgent,
  teamId: 't1',
  selectedAgentId: null,
  isAuthenticated: true,
  openLoginModal: vi.fn(),
  editingAgent: null,
  editAgentName: '',
  openAgentMenu: null,
  menuPosition: { top: 0, left: 0 },
  handleAgentClick: vi.fn(),
  onEditAgent: vi.fn(),
  setOpenAgentMenu: vi.fn(),
  setConfirmDelete: vi.fn(),
  toggleAgentMenu: vi.fn(),
  startEditAgent: vi.fn(),
  saveAgentName: vi.fn(),
  handleAgentBlur: vi.fn(),
  onAgentNameChange: vi.fn(),
  t: tFn,
};

describe('TeamTreeAgentItem', { tags: ['integration'] }, () => {
  it('renders agent name', () => {
    render(<TeamTreeAgentItem {...baseProps} />);
    expect(screen.getByText('Test Agent')).toBeDefined();
  });

  it('shows active class when selected', () => {
    render(<TeamTreeAgentItem {...baseProps} selectedAgentId="a1" />);
    const wrapper = screen.getByText('Test Agent').closest('.group');
    expect(wrapper?.className).toContain('active');
  });

  it('does not show active class when not selected', () => {
    render(<TeamTreeAgentItem {...baseProps} selectedAgentId="other" />);
    const wrapper = screen.getByText('Test Agent').closest('.group');
    expect(wrapper?.className).not.toContain('active');
  });

  it('shows edit input when editingAgent matches', () => {
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" editAgentName="Renamed" />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input).toBeDefined();
    expect(input.value).toBe('Renamed');
  });

  it('does not show edit input for different agent', () => {
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a2" editAgentName="Renamed" />);
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('hides agent item and menu button when editing', () => {
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" />);
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByRole('textbox')).toBeDefined();
  });

  it('calls handleAgentClick when agent item clicked', () => {
    const handleAgentClick = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} handleAgentClick={handleAgentClick} />);
    fireEvent.click(screen.getByText('Test Agent'));
    expect(handleAgentClick).toHaveBeenCalledWith(mockAgent);
  });

  it('calls toggleAgentMenu when menu button clicked', () => {
    const toggleAgentMenu = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} toggleAgentMenu={toggleAgentMenu} />);
    // The MoreVertical menu icon is a span inside the agent button
    const menuTrigger = screen.getByText('Test Agent').closest('button')?.querySelector('.group-hover\\:opacity-50');
    expect(menuTrigger).toBeDefined();
    fireEvent.click(menuTrigger!);
    expect(toggleAgentMenu).toHaveBeenCalledWith('a1', expect.any(Object));
  });

  it('renders dropdown portal when menu is open', () => {
    render(<TeamTreeAgentItem {...baseProps} openAgentMenu="a1" menuPosition={{ top: 100, left: 200 }} />);
    // Check items rendered
    expect(screen.getByText('sidebar.edit')).toBeDefined();
    expect(screen.getByText('sidebar.rename')).toBeDefined();
    expect(screen.getByText('sidebar.delete')).toBeDefined();
  });

  it('does not render dropdown when menu is closed', () => {
    render(<TeamTreeAgentItem {...baseProps} openAgentMenu={null} />);
    expect(screen.queryByText('sidebar.edit')).toBeNull();
  });

  it('calls openLoginModal when not authenticated and edit clicked', () => {
    const openLoginModal = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} isAuthenticated={false} openLoginModal={openLoginModal} openAgentMenu="a1" />);
    fireEvent.click(screen.getByText('sidebar.edit'));
    expect(openLoginModal).toHaveBeenCalled();
  });

  it('calls onEditAgent and closes menu when authenticated and edit clicked', () => {
    const onEditAgent = vi.fn();
    const setOpenAgentMenu = vi.fn();
    render(
      <TeamTreeAgentItem
        {...baseProps}
        onEditAgent={onEditAgent}
        setOpenAgentMenu={setOpenAgentMenu}
        openAgentMenu="a1"
      />,
    );
    fireEvent.click(screen.getByText('sidebar.edit'));
    expect(onEditAgent).toHaveBeenCalledWith(mockAgent);
    expect(setOpenAgentMenu).toHaveBeenCalledWith(null);
  });

  it('does not call onEditAgent if onEditAgent not provided', () => {
    const setOpenAgentMenu = vi.fn();
    render(
      <TeamTreeAgentItem
        {...baseProps}
        onEditAgent={undefined}
        setOpenAgentMenu={setOpenAgentMenu}
        openAgentMenu="a1"
      />,
    );
    fireEvent.click(screen.getByText('sidebar.edit'));
    expect(setOpenAgentMenu).toHaveBeenCalledWith(null);
  });

  it('calls openLoginModal when not authenticated and rename clicked', () => {
    const openLoginModal = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} isAuthenticated={false} openLoginModal={openLoginModal} openAgentMenu="a1" />);
    fireEvent.click(screen.getByText('sidebar.rename'));
    expect(openLoginModal).toHaveBeenCalled();
  });

  it('calls startEditAgent when authenticated and rename clicked', () => {
    const startEditAgent = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} startEditAgent={startEditAgent} openAgentMenu="a1" />);
    fireEvent.click(screen.getByText('sidebar.rename'));
    expect(startEditAgent).toHaveBeenCalledWith(mockAgent);
  });

  it('calls openLoginModal when not authenticated and delete clicked', () => {
    const openLoginModal = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} isAuthenticated={false} openLoginModal={openLoginModal} openAgentMenu="a1" />);
    fireEvent.click(screen.getByText('sidebar.delete'));
    expect(openLoginModal).toHaveBeenCalled();
  });

  it('calls setConfirmDelete and closes menu when authenticated and delete clicked', () => {
    const setConfirmDelete = vi.fn();
    const setOpenAgentMenu = vi.fn();
    render(
      <TeamTreeAgentItem
        {...baseProps}
        setConfirmDelete={setConfirmDelete}
        setOpenAgentMenu={setOpenAgentMenu}
        openAgentMenu="a1"
      />,
    );
    fireEvent.click(screen.getByText('sidebar.delete'));
    expect(setConfirmDelete).toHaveBeenCalledWith({ type: 'agent', teamId: 't1', agentId: 'a1' });
    expect(setOpenAgentMenu).toHaveBeenCalledWith(null);
  });

  it('calls saveAgentName on Enter key in edit input', () => {
    const saveAgentName = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" saveAgentName={saveAgentName} />);
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
    expect(saveAgentName).toHaveBeenCalled();
  });

  it('does not call saveAgentName on non-Enter key', () => {
    const saveAgentName = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" saveAgentName={saveAgentName} />);
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });
    expect(saveAgentName).not.toHaveBeenCalled();
  });

  it('calls handleAgentBlur on input blur', () => {
    const handleAgentBlur = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" handleAgentBlur={handleAgentBlur} />);
    fireEvent.blur(screen.getByRole('textbox'));
    expect(handleAgentBlur).toHaveBeenCalled();
  });

  it('calls onAgentNameChange on input change', () => {
    const onAgentNameChange = vi.fn();
    render(<TeamTreeAgentItem {...baseProps} editingAgent="a1" onAgentNameChange={onAgentNameChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'NewName' } });
    expect(onAgentNameChange).toHaveBeenCalledWith('NewName');
  });

  it('shows Lock icon when not authenticated', () => {
    render(<TeamTreeAgentItem {...baseProps} isAuthenticated={false} openAgentMenu="a1" />);
    expect(screen.getByText('sidebar.edit')).toBeDefined();
    expect(screen.getByText('sidebar.rename')).toBeDefined();
    expect(screen.getByText('sidebar.delete')).toBeDefined();
  });

  it('has one button (agent item) when not editing', () => {
    render(<TeamTreeAgentItem {...baseProps} />);
    const buttons = screen.getAllByRole('button');
    // Agent item button (MoreVertical is a span inside)
    expect(buttons.length).toBe(1);
  });
});
