import VersionPager from '../VersionPager';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

describe('VersionPager', () => {
  it('returns null when total is below 2', () => {
    const { container } = render(<VersionPager total={1} current={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows current/total counter', () => {
    render(<VersionPager total={3} current={1} />);
    expect(screen.getByText('2/3')).toBeInTheDocument();
  });

  it('disables prev at first version and next at last', () => {
    render(<VersionPager total={3} current={0} />);
    expect(
      screen.getByRole('button', { name: 'Previous user version' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Next user version' }),
    ).toBeEnabled();
  });

  it('fires onPrev/onNext callbacks', () => {
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <VersionPager
        total={3}
        current={1}
        onPrev={onPrev}
        onNext={onNext}
        prevLabel="前"
        nextLabel="后"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: '前' }));
    expect(onPrev).toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '后' }));
    expect(onNext).toHaveBeenCalled();
  });
});
