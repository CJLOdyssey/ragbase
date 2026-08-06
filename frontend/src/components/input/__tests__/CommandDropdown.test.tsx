import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TestProviders } from '@/test/setup';
import CommandDropdown from '@/components/input/CommandDropdown';
import type { CommandOption } from '@/types/input';

function makeCmd(id: string, overrides: Partial<CommandOption> = {}): CommandOption {
  return {
    id,
    name: 'cmd-' + id,
    source: 'local' as const,
    ...overrides,
  };
}

describe('CommandDropdown', { tags: ['unit'] }, () => {
  const onSelect = vi.fn();
  const onHover = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no commands', () => {
    const { container } = render(
      <TestProviders>
        <CommandDropdown commands={[]} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    expect(container.querySelector('[class*="text-center"]')).toBeTruthy();
  });

  it('renders command list', () => {
    const cmds = [makeCmd('1', { name: 'search' }), makeCmd('2', { name: 'deploy' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    expect(screen.getByText('/search')).toBeInTheDocument();
    expect(screen.getByText('/deploy')).toBeInTheDocument();
  });

  it('sets aria-selected on active item', () => {
    const cmds = [makeCmd('1', { name: 'a' }), makeCmd('2', { name: 'b' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    expect(options[1]).toHaveAttribute('aria-selected', 'false');
  });

  it('calls onSelect when clicking an option', () => {
    const cmds = [makeCmd('1', { name: 'search' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('/search'));
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it('calls onHover on mouseenter', () => {
    const cmds = [makeCmd('1', { name: 'a' }), makeCmd('2', { name: 'b' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.mouseEnter(screen.getByText('/b'));
    expect(onHover).toHaveBeenCalledWith(1);
  });

  it('shows agent source badge', () => {
    const cmds = [makeCmd('1', { name: 'agent-cmd', source: 'agent' as const })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('shows description when present', () => {
    const cmds = [makeCmd('1', { name: 'search', description: 'Search files' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    expect(screen.getByText('Search files')).toBeInTheDocument();
  });

  it('closes on outside click', () => {
    const cmds = [makeCmd('1', { name: 'search' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.mouseDown(document.body);
    expect(onClose).toHaveBeenCalled();
  });

  it('does not close on inside click', () => {
    const cmds = [makeCmd('1', { name: 'search' })];
    render(
      <TestProviders>
        <CommandDropdown commands={cmds} activeIndex={0} onSelect={onSelect} onHover={onHover} onClose={onClose} />
      </TestProviders>,
    );
    const popover = document.querySelector('[role="listbox"]')!;
    fireEvent.mouseDown(popover);
    expect(onClose).not.toHaveBeenCalled();
  });
});
