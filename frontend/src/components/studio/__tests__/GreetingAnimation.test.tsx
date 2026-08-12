import GreetingAnimation from '../GreetingAnimation';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: () => '你好，欢迎',
    i18n: { language: 'zh-CN' },
  }),
}));

describe('GreetingAnimation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the full greeting immediately under reduced motion', () => {
    window.matchMedia = vi.fn().mockImplementation(() => ({
      matches: true,
      media: '',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const onComplete = vi.fn();
    render(<GreetingAnimation onComplete={onComplete} />);
    expect(screen.getByText('你好，欢迎')).toBeInTheDocument();
    expect(onComplete).toHaveBeenCalled();
  });

  it('types the greeting progressively and calls onComplete', () => {
    window.matchMedia = vi.fn().mockImplementation(() => ({
      matches: false,
      media: '',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const onComplete = vi.fn();
    render(<GreetingAnimation onComplete={onComplete} />);
    // initial render shows empty text with a cursor
    expect(screen.getByRole('heading')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(100 * 6);
    });
    expect(onComplete).toHaveBeenCalled();
  });
});
