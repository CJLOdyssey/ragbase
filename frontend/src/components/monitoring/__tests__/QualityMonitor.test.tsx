import { TestProviders } from '../../../test/setup';
import type { MonitoringSummary } from '../../../types/monitoring';
import QualityMonitor from '../QualityMonitor';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks } = vi.hoisted(() => ({
  mocks: { fetchMonitoringSummary: vi.fn() },
}));

vi.mock('../../../api/client/monitoring', () => mocks);

const EMPTY: MonitoringSummary = {
  window_hours: 24,
  retrieval: {
    total: 0,
    empty_recall_count: 0,
    empty_recall_rate: 0,
    latency_p50_ms: null,
    latency_p95_ms: null,
  },
  feedback: { total: 0, good_count: 0, bad_count: 0, good_ratio: null },
  alerts: [],
};

const HEALTHY: MonitoringSummary = {
  window_hours: 24,
  retrieval: {
    total: 120,
    empty_recall_count: 4,
    empty_recall_rate: 0.0333,
    latency_p50_ms: 480,
    latency_p95_ms: 2100,
  },
  feedback: { total: 20, good_count: 18, bad_count: 2, good_ratio: 0.9 },
  alerts: [],
};

const ALERTING: MonitoringSummary = {
  ...HEALTHY,
  retrieval: { ...HEALTHY.retrieval, empty_recall_rate: 0.32 },
  feedback: { ...HEALTHY.feedback, good_ratio: 0.4 },
  alerts: [
    { level: 'warning', code: 'empty_recall_high', current: 32, threshold: 15 },
    {
      level: 'warning',
      code: 'p95_latency_high',
      current: 9000,
      threshold: 8000,
    },
    { level: 'warning', code: 'good_ratio_low', current: 0.4, threshold: 0.6 },
  ],
};

function renderPage() {
  return render(
    <TestProviders>
      <QualityMonitor />
    </TestProviders>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.fetchMonitoringSummary.mockResolvedValue(EMPTY);
});

describe('QualityMonitor', { tags: ['unit'] }, () => {
  it('renders title and empty states when no data', async () => {
    renderPage();
    expect(await screen.findByText('质量监控')).toBeTruthy();
    expect((await screen.findAllByText('暂无数据')).length).toBeGreaterThan(0);
    expect(screen.getByText('暂无反馈')).toBeTruthy();
    expect(screen.getByText('当前无告警')).toBeTruthy();
  });

  it('renders metric cards with formatted values', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    renderPage();
    expect(await screen.findByText('120')).toBeTruthy();
    expect(screen.getByText('3.3%')).toBeTruthy();
    expect(screen.getByText('480ms')).toBeTruthy();
    expect(screen.getByText('2100ms')).toBeTruthy();
    expect(screen.getByText('90.0%')).toBeTruthy();
    expect(screen.getByText('18')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
  });

  it('switches window and refetches', async () => {
    renderPage();
    const weekBtn = await screen.findByTestId('window-168');
    fireEvent.click(weekBtn);
    expect(mocks.fetchMonitoringSummary).toHaveBeenLastCalledWith(168);
  });

  it('renders alerts with formatted values', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(ALERTING);
    renderPage();
    expect(await screen.findByTestId('alert-empty_recall_high')).toBeTruthy();
    expect(screen.getByTestId('alert-p95_latency_high')).toBeTruthy();
    expect(screen.getByTestId('alert-good_ratio_low')).toBeTruthy();
    expect(screen.getByText(/32\.0% 超过阈值 15\.0%/)).toBeTruthy();
    expect(screen.getByText(/9000ms 超过阈值 8000ms/)).toBeTruthy();
    expect(screen.getByText(/40\.0% 低于阈值 60\.0%/)).toBeTruthy();
  });

  it('does not render alert list when healthy', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    renderPage();
    await screen.findByText('当前无告警');
    expect(screen.queryByTestId('alert-empty_recall_high')).toBeNull();
  });
});
