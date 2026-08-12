import BrowserFrame from '../BrowserFrame';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

const FRAME_EVENT = 'browser-frame';
const URL_EVENT = 'browser-open-url';
const CLEAR_EVENT = 'clear-browser-url';

function dispatch(name: string, detail?: string) {
  act(() => {
    window.dispatchEvent(new CustomEvent(name, { detail: detail ?? '' }));
  });
}

describe('BrowserFrame', () => {
  it('renders nothing by default', () => {
    const { container } = render(<BrowserFrame />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows a screenshot when browser-frame event fires', () => {
    render(<BrowserFrame />);
    dispatch(FRAME_EVENT, 'aGVsbG8=');
    expect(screen.getByText('Browser screenshot')).toBeInTheDocument();
    const img = document.querySelector('img') as HTMLImageElement;
    expect(img.src).toContain('data:image/png;base64,aGVsbG8=');
  });

  it('shows an iframe when browser-open-url fires', () => {
    render(<BrowserFrame />);
    dispatch(URL_EVENT, 'https://example.com');
    expect(document.querySelector('iframe')).toHaveAttribute(
      'src',
      'https://example.com',
    );
  });

  it('clears the frame on clear event', () => {
    render(<BrowserFrame />);
    dispatch(FRAME_EVENT, 'aGVsbG8=');
    expect(screen.getByText('Browser screenshot')).toBeInTheDocument();
    dispatch(CLEAR_EVENT);
    expect(screen.queryByText('Browser screenshot')).not.toBeInTheDocument();
  });

  it('closes the frame via the X button', () => {
    render(<BrowserFrame />);
    dispatch(FRAME_EVENT, 'aGVsbG8=');
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText('Browser screenshot')).not.toBeInTheDocument();
  });
});
