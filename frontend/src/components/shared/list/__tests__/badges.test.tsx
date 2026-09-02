import { TestProviders } from '../../../../test/setup';
import {
  ActionButton,
  MonoBadge,
  StatusPill,
  Tag,
} from '../badges';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

describe('StatusPill', { tags: ['unit'] }, () => {
  it('renders label with color style', () => {
    render(
      <TestProviders>
        <StatusPill label="已索引" color="#22c55e" testId="status-indexed" />
      </TestProviders>,
    );
    const el = screen.getByTestId('status-indexed');
    expect(el.textContent).toBe('已索引');
    expect(el.style.color).toBeTruthy();
  });

  it('renders dot when requested', () => {
    render(
      <TestProviders>
        <StatusPill label="活跃" color="#fff" dot testId="p1" />
      </TestProviders>,
    );
    const el = screen.getByTestId('p1');
    const dot = el.querySelector('span');
    expect(dot).not.toBeNull();
  });

  it('capsule shape (rounded-full baseline)', () => {
    render(
      <TestProviders>
        <StatusPill label="x" color="#fff" testId="p2" />
      </TestProviders>,
    );
    expect(screen.getByTestId('p2').className).toContain('rounded-full');
  });
});

describe('MonoBadge / Tag', { tags: ['unit'] }, () => {
  it('MonoBadge renders monospace chip', () => {
    render(
      <TestProviders>
        <MonoBadge>v3</MonoBadge>
      </TestProviders>,
    );
    expect(screen.getByText('v3').className).toContain('font-mono');
  });

  it('Tag renders category chip', () => {
    render(
      <TestProviders>
        <Tag>翻译</Tag>
      </TestProviders>,
    );
    expect(screen.getByText('翻译')).toBeInTheDocument();
  });
});

describe('ActionButton', { tags: ['unit'] }, () => {
  it('renders 27px square button', () => {
    render(
      <TestProviders>
        <ActionButton title="删除" hoverVar="--color-danger" onClick={() => {}}>
          x
        </ActionButton>
      </TestProviders>,
    );
    expect(screen.getByTitle('删除').className).toContain('w-[27px]');
  });

  it('stops click propagation (row click not fired)', () => {
    const onAction = vi.fn();
    const onRow = vi.fn();
    render(
      // @ts-expect-error test-only div row
      <div onClick={onRow}>
        <ActionButton
          title="更多"
          hoverVar="--color-accent"
          onClick={onAction}
          data-testid="more-1"
        />
      </div>,
    );
    fireEvent.click(screen.getByTestId('more-1'));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onRow).not.toHaveBeenCalled();
  });

  it('disabled blocks interaction', () => {
    const onAction = vi.fn();
    render(
      <TestProviders>
        <ActionButton
          title="索引"
          hoverVar="--color-accent"
          onClick={onAction}
          disabled
          data-testid="idx-1"
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByTestId('idx-1'));
    expect(onAction).not.toHaveBeenCalled();
  });

  it('injects --hover css variable from hoverVar', () => {
    render(
      <TestProviders>
        <ActionButton title="t" hoverVar="--color-accent" onClick={() => {}} />
      </TestProviders>,
    );
    const btn = screen.getByTitle('t') as HTMLElement;
    expect(btn.style.getPropertyValue('--hover')).toBe(
      'var(--color-accent)',
    );
  });
});
