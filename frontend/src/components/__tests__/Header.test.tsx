import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Header from '../Header';
import { expectNoA11yViolations } from '../../test/a11y-setup';

describe('Header', { tags: ['unit'] }, () => {
  it('renders sidebar toggle button', () => {
    render(<Header onToggleSidebar={vi.fn()} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls onToggleSidebar when button is clicked', async () => {
    const onToggleSidebar = vi.fn();
    render(<Header onToggleSidebar={onToggleSidebar} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button'));
    expect(onToggleSidebar).toHaveBeenCalledTimes(1);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<Header onToggleSidebar={vi.fn()} />);
    await expectNoA11yViolations(container);
  });
});
