import type { Message } from '../../../types/studio';
import UserMessage from '../UserMessage';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

function makeMsg(overrides: Partial<Message>): Message {
  return {
    id: 'm1',
    role: 'user',
    content: '原始问题',
    ...overrides,
  };
}

const noop = () => {};

function renderUser(msg: Message, extra: Record<string, unknown> = {}) {
  return render(
    <UserMessage
      msg={msg}
      onEditMessage={noop}
      onSwitchUserVersion={noop}
      {...extra}
    />,
  );
}

describe('UserMessage', () => {
  it('renders message content', () => {
    renderUser(makeMsg({}));
    expect(screen.getByText('原始问题')).toBeInTheDocument();
  });

  it('renders attachments as links', () => {
    renderUser(
      makeMsg({ attachments: [{ id: 'att1', filename: 'report.pdf' }] }),
    );
    const link = screen.getByText('report.pdf').closest('a');
    expect(link).toHaveAttribute('href', '/api/attachments/att1');
  });

  it('shows timestamp when provided', () => {
    renderUser(makeMsg({ timestamp: Date.UTC(2026, 0, 1, 8, 30) }));
    expect(screen.getByText(/08:30|16:30/)).toBeInTheDocument();
  });

  it('starts editing via edit button and saves trimmed content', () => {
    const onEditMessage = vi.fn();
    renderUser(makeMsg({}), { onEditMessage });
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: ' 修改后的问题 ' } });
    fireEvent.click(screen.getByText('common.send'));
    expect(onEditMessage).toHaveBeenCalledWith('m1', '修改后的问题');
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('cancels editing without saving', () => {
    const onEditMessage = vi.fn();
    renderUser(makeMsg({}), { onEditMessage });
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: '改了一半' },
    });
    fireEvent.click(screen.getByText('common.cancel'));
    expect(onEditMessage).not.toHaveBeenCalled();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('saves on Enter without shift', () => {
    const onEditMessage = vi.fn();
    renderUser(makeMsg({}), { onEditMessage });
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'enter 保存' },
    });
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
    expect(onEditMessage).toHaveBeenCalledWith('m1', 'enter 保存');
  });

  it('cancels on Escape', () => {
    renderUser(makeMsg({}));
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('does not save empty edits', () => {
    const onEditMessage = vi.fn();
    renderUser(makeMsg({}), { onEditMessage });
    fireEvent.click(screen.getByRole('button', { name: 'teamMessage.edit' }));
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '   ' } });
    fireEvent.click(screen.getByText('common.send'));
    expect(onEditMessage).not.toHaveBeenCalled();
  });

  it('renders version pager with multiple user versions', () => {
    const onSwitchUserVersion = vi.fn();
    renderUser(makeMsg({ userVersions: ['v1', 'v2'], currentUserVersion: 1 }), {
      onSwitchUserVersion,
    });
    expect(screen.getByText('2/2')).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: 'Previous user version' }),
    );
    expect(onSwitchUserVersion).toHaveBeenCalledWith('m1', 'prev');
  });

  it('does not render version pager with single version', () => {
    renderUser(makeMsg({}));
    expect(screen.queryByText('1/1')).not.toBeInTheDocument();
  });
});
