import type { Message } from '../../../types/studio';
import { ThinkingSection } from '../ThinkingSection';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

const t = (k: string) => k;

function makeMsg(overrides: Partial<Message>): Message {
  return { id: 'm1', role: 'agent', content: '', ...overrides };
}

function renderSection(msg: Message, extra: Record<string, unknown> = {}) {
  return render(
    <ThinkingSection msg={msg} color="text-blue-500" t={t} {...extra} />,
  );
}

describe('ThinkingSection', () => {
  it('renders nothing without thinking text', () => {
    const { container } = renderSection(makeMsg({}));
    expect(container).toBeEmptyDOMElement();
  });

  it('renders done state with estimated seconds', () => {
    renderSection(makeMsg({ thinking: 'x'.repeat(120), thinkingDone: true }));
    expect(
      screen.getByText('teamMessage.thinkingComplete'),
    ).toBeInTheDocument();
    expect(screen.getByText(/^2teamMessage\.seconds$/)).toBeInTheDocument();
  });

  it('renders stopped state when showContinue', () => {
    renderSection(makeMsg({ thinking: '部分推理' }), { showContinue: true });
    expect(screen.getByText('teamMessage.thinkingStopped')).toBeInTheDocument();
    expect(screen.getByText('部分推理')).toBeInTheDocument();
  });

  it('renders pending state while streaming', () => {
    renderSection(makeMsg({ thinking: '思考中' }));
    expect(screen.getByText('teamMessage.thinkingPending')).toBeInTheDocument();
  });

  it('collapses and expands the thinking body', () => {
    renderSection(makeMsg({ thinking: '可见推理', thinkingDone: true }));
    expect(screen.getByText('可见推理')).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: /teamMessage.thinkingComplete/ }),
    );
    expect(screen.queryByText('可见推理')).not.toBeInTheDocument();
  });

  it('renders grouped tool-call thinking nodes', () => {
    renderSection(
      makeMsg({
        thinking: '[tools] python\n\n[result] ok',
        thinkingDone: true,
      }),
    );
    expect(screen.getByText(/\[tools\]/)).toBeInTheDocument();
  });
});
