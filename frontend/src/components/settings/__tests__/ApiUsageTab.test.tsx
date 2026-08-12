import ApiUsageTab from '../ApiUsageTab';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const USAGE = {
  today_requests: 10,
  today_tokens: 2000,
  month_requests: 300,
  month_tokens: 40000,
};

describe('ApiUsageTab', { tags: ['unit'] }, () => {
  it('renders the four stat cards with labels and values', () => {
    render(<ApiUsageTab usage={USAGE} />);
    expect(screen.getByText('api.usageStats')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('api.todayRequests')).toBeInTheDocument();
    expect(screen.getByText('2,000')).toBeInTheDocument();
    expect(screen.getByText('api.todayTokens')).toBeInTheDocument();
    expect(screen.getByText('300')).toBeInTheDocument();
    expect(screen.getByText('api.monthRequests')).toBeInTheDocument();
    expect(screen.getByText('40,000')).toBeInTheDocument();
    expect(screen.getByText('api.monthTokens')).toBeInTheDocument();
  });

  it('renders nothing extra when keyUsage is absent or empty', () => {
    const { rerender } = render(<ApiUsageTab usage={USAGE} />);
    expect(screen.queryByText('providerEdit.usageDetail')).toBeNull();
    rerender(<ApiUsageTab usage={USAGE} keyUsage={[]} />);
    expect(screen.queryByText('providerEdit.usageDetail')).toBeNull();
  });

  it('renders per-key usage rows with label fallback and last-used date', () => {
    render(
      <ApiUsageTab
        usage={USAGE}
        keyUsage={[
          {
            label: 'OpenAI 主',
            provider: 'openai',
            capabilities: ['llm'],
            is_active: true,
            last_used_at: '2026-08-01T00:00:00Z',
            today_requests: 5,
            today_tokens: 100,
            month_requests: 50,
            month_tokens: 5000,
          },
          {
            label: '',
            provider: 'deepseek',
            capabilities: ['chat'],
            is_active: false,
            last_used_at: null,
          },
        ]}
      />,
    );
    expect(screen.getByText('providerEdit.usageDetail')).toBeInTheDocument();
    expect(screen.getByText('OpenAI 主')).toBeInTheDocument();
    // 无 label → 回退 provider 名（label 行与 provider 副行各出现一次）
    expect(screen.getAllByText('deepseek')).toHaveLength(2);
    expect(
      screen.getAllByText(/providerEdit.today/).length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getAllByText(/providerEdit.thisMonth/).length,
    ).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/providerEdit.lastUsedAt/)).toBeInTheDocument();
  });
});
