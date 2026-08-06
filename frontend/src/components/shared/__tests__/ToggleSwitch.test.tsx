import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ToggleSwitch from '@/components/shared/ToggleSwitch';
import { expectNoA11yViolations } from '@/test/a11y-setup';

describe('ToggleSwitch', { tags: ['unit'] }, () => {
  it('renders checkbox with checked state', () => {
    render(<ToggleSwitch checked={true} onChange={vi.fn()} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeChecked();
  });

  it('renders checkbox with unchecked state', () => {
    render(<ToggleSwitch checked={false} onChange={vi.fn()} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).not.toBeChecked();
  });

  it('calls onChange when toggled', () => {
    const onChange = vi.fn();
    render(<ToggleSwitch checked={false} onChange={onChange} />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('renders with sm size', () => {
    const { container } = render(<ToggleSwitch checked={false} onChange={vi.fn()} size="sm" />);
    // sm size renders label with w-9 (20px) vs md w-10 (24px)
    expect(container.querySelector('label[class*="w-9"]')).toBeInTheDocument();
  });

  it('renders with md size by default', () => {
    const { container } = render(<ToggleSwitch checked={false} onChange={vi.fn()} />);
    // md size renders label with w-10 (24px) Tailwind class
    expect(container.querySelector('label[class*="w-10"]')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ToggleSwitch checked={false} onChange={() => {}} />);
    await expectNoA11yViolations(container);
  });

  it('has no accessibility violations when checked', async () => {
    const { container } = render(<ToggleSwitch checked={true} onChange={() => {}} />);
    await expectNoA11yViolations(container);
  });
});
