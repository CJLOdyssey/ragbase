import { useRef } from 'react';
import { TestProviders } from '../../../../test/setup';
import { useRowMenu } from '../useRowMenu';
import { createPortal } from 'react-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

function Harness({ id = 'row-1' }: { id?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { openId, pos, registerTrigger, toggle, close } = useRowMenu({
    containerRef,
    menuRef,
  });
  return (
    <div ref={containerRef}>
      <button
        type="button"
        data-testid="trigger"
        onClick={() => toggle(id)}
      />
      <span data-testid="open">{String(openId)}</span>
      <span data-testid="pos">{pos ? `${pos.top}-${pos.right}` : 'none'}</span>
      {registerTrigger && (
        <span
          ref={(el) => {
            // simulate trigger registration on mount
            registerTrigger(id, el);
          }}
        />
      )}
      {openId === id &&
        pos &&
        createPortal(
          <div ref={menuRef} data-testid="menu">
            <button type="button" data-testid="close" onClick={close}>
              close
            </button>
          </div>,
          document.body,
        )}
    </div>
  );
}

describe('useRowMenu', { tags: ['unit'] }, () => {
  it('toggle opens with computed position; toggle again closes', () => {
    render(
      <TestProviders>
        <Harness />
      </TestProviders>,
    );
    expect(screen.getByTestId('open').textContent).toBe('null');
    fireEvent.click(screen.getByTestId('trigger'));
    expect(screen.getByTestId('open').textContent).toBe('row-1');
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    expect(screen.getByTestId('pos').textContent).not.toBe('none');
    fireEvent.click(screen.getByTestId('trigger'));
    expect(screen.getByTestId('open').textContent).toBe('null');
  });

  it('outside mousedown closes the menu', () => {
    render(
      <TestProviders>
        <Harness />
      </TestProviders>,
    );
    fireEvent.click(screen.getByTestId('trigger'));
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    fireEvent.mouseDown(document.body);
    expect(screen.getByTestId('open').textContent).toBe('null');
  });

  it('mousedown inside portal menu does NOT close', () => {
    render(
      <TestProviders>
        <Harness />
      </TestProviders>,
    );
    fireEvent.click(screen.getByTestId('trigger'));
    fireEvent.mouseDown(screen.getByTestId('menu'));
    expect(screen.getByTestId('open').textContent).toBe('row-1');
  });

  it('close() clears state', () => {
    render(
      <TestProviders>
        <Harness />
      </TestProviders>,
    );
    fireEvent.click(screen.getByTestId('trigger'));
    fireEvent.click(screen.getByTestId('close'));
    expect(screen.queryByTestId('menu')).toBeNull();
  });
});
