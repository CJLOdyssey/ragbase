import { TestProviders } from '../../../test/setup';
import type {
  MonitoringSummary,
  MonitoringTimeseries,
  RootCauseBreakdown,
  TopQueriesResponse,
} from '../../../types/monitoring';
import QualityMonitor from '../QualityMonitor';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { SettingsProvider } from '../../../contexts/SettingsContext';
import { ToastProvider } from '../../../utils/useToast';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks } = vi.hoisted(() => ({
  mocks: {
    fetchMonitoringSummary: vi.fn(),
    fetchMonitoringTimeseries: vi.fn(),
    fetchRootCauses: vi.fn(),
    fetchTopQueries: vi.fn(),
    fetchBadFeedback: vi.fn(),
    reviewBadFeedback: vi.fn(),
  },
}));

vi.mock('../../../api/client/monitoring', () => mocks);

const EMPTY: MonitoringSummary = {
  window_hours: 24,
  retrieval: {
    total: 0,
    empty_recall_count: 0,
    empty_recall_rate: 0,
    avg_hit_count: null,
    latency_p50_ms: null,
    latency_p95_ms: null,
  },
  feedback: { total: 0, good_count: 0, bad_count: 0, good_ratio: null, answered_runs: 0 },
  alerts: [],
};

const EMPTY_TS: MonitoringTimeseries = {
  window_hours: 24,
  bucket_hours: 1,
  previous_points: null,
  points: [
    {
      ts: '2026-08-23T00:00:00+00:00',
      retrievals: 0,
      empty_count: 0,
      avg_hits: null,
      avg_latency_ms: null,
      good: 0,
      bad: 0,
    },
    {
      ts: '2026-08-23T01:00:00+00:00',
      retrievals: 0,
      empty_count: 0,
      avg_hits: null,
      avg_latency_ms: null,
      good: 0,
      bad: 0,
    },
  ],
};

const TS_WITH_DATA: MonitoringTimeseries = {
  window_hours: 24,
  bucket_hours: 1,
  previous_points: [
    {
      ts: '2026-08-22T00:00:00+00:00',
      retrievals: 8,
      empty_count: 1,
      avg_hits: 2.0,
      avg_latency_ms: 350,
      latency_p50_ms: 320,
      latency_p95_ms: 900,
      good: 2,
      bad: 1,
    },
    {
      ts: '2026-08-22T01:00:00+00:00',
      retrievals: 20,
      empty_count: 3,
      avg_hits: 3.0,
      avg_latency_ms: 420,
      latency_p50_ms: 400,
      latency_p95_ms: 1200,
      good: 6,
      bad: 2,
    },
  ],
  points: [
    {
      ts: '2026-08-23T00:00:00+00:00',
      retrievals: 10,
      empty_count: 2,
      avg_hits: 2.5,
      avg_latency_ms: 300,
      good: 4,
      bad: 1,
    },
    {
      ts: '2026-08-23T01:00:00+00:00',
      retrievals: 30,
      empty_count: 1,
      avg_hits: 4.0,
      avg_latency_ms: 500,
      good: 9,
      bad: 1,
    },
  ],
};

const HEALTHY: MonitoringSummary = {
  window_hours: 24,
  retrieval: {
    total: 120,
    empty_recall_count: 4,
    empty_recall_rate: 0.0333,
    avg_hit_count: 3.5,
    latency_p50_ms: 480,
    latency_p95_ms: 2100,
  },
  feedback: { total: 20, good_count: 18, bad_count: 2, good_ratio: 0.9, answered_runs: 120 },
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

const ROOT_CAUSES_EMPTY: RootCauseBreakdown = {
  window_hours: 24,
  total_bad: 0,
  pending: 0,
  resolved: 0,
  dismissed: 0,
  causes: [
    { cause: 'retrieval_miss', count: 0 },
    { cause: 'wrong_answer', count: 0 },
    { cause: 'bad_format', count: 0 },
    { cause: 'other', count: 0 },
  ],
};

const ROOT_CAUSES_DATA: RootCauseBreakdown = {
  window_hours: 24,
  total_bad: 3,
  pending: 1,
  resolved: 2,
  dismissed: 0,
  causes: [
    { cause: 'retrieval_miss', count: 2 },
    { cause: 'wrong_answer', count: 1 },
    { cause: 'bad_format', count: 0 },
    { cause: 'other', count: 0 },
  ],
};

const TOPQ_EMPTY: TopQueriesResponse = {
  window_hours: 24,
  kind: 'empty',
  items: [],
};

const TOPQ_EMPTY_DATA: TopQueriesResponse = {
  window_hours: 24,
  kind: 'empty',
  items: [
    { query: 'gap query', count: 3, avg_latency_ms: null },
    { query: 'minor gap', count: 1, avg_latency_ms: null },
  ],
};

const BAD_FEEDBACK_EMPTY = {
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
};

function renderPage() {
  return render(
    <TestProviders>
      <QualityMonitor />
    </TestProviders>,
  );
}

/** 需要 Router 初始 location 的场景（深链 / URL 回写断言）。 */
function renderMonitorAt(
  initialEntries: string[],
  onSearch?: (search: string) => void,
) {
  function UrlProbe() {
    const { search } = useLocation();
    if (onSearch) onSearch(search);
    return null;
  }
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <SettingsProvider>
          <ToastProvider>
            <QualityMonitor />
            <UrlProbe />
          </ToastProvider>
        </SettingsProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function openTab(testId: string) {
  fireEvent.click(await screen.findByTestId(`monitoring-tab-${testId}`));
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.fetchMonitoringSummary.mockResolvedValue(EMPTY);
  mocks.fetchMonitoringTimeseries.mockResolvedValue(EMPTY_TS);
  mocks.fetchRootCauses.mockResolvedValue(ROOT_CAUSES_EMPTY);
  mocks.fetchTopQueries.mockResolvedValue(TOPQ_EMPTY);
  mocks.fetchBadFeedback.mockResolvedValue(BAD_FEEDBACK_EMPTY);
});

describe('QualityMonitor', { tags: ['unit'] }, () => {
  it('renders title and empty states when no data', async () => {
    renderPage();
    expect(await screen.findByText('质量监控')).toBeTruthy();
    expect((await screen.findAllByText('—')).length).toBeGreaterThan(0);
    expect(screen.getByText('当前无告警')).toBeTruthy();
  });

  it('renders overview KPI cards with formatted values from real aggregates', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    renderPage();
    expect(await screen.findByText('120')).toBeTruthy();
    expect(screen.getByText('480ms')).toBeTruthy();
    expect(screen.getByText('90.0%')).toBeTruthy();
  });

  it('switches window and refetches both endpoints', async () => {
    renderPage();
    const weekBtn = await screen.findByTestId('window-168');
    fireEvent.click(weekBtn);
    expect(mocks.fetchMonitoringSummary).toHaveBeenLastCalledWith({
      window_hours: 168,
    });
    // 预设窗口请求上期序列（真·环比基线 + ghost 虚线）。
    expect(mocks.fetchMonitoringTimeseries).toHaveBeenLastCalledWith(
      { window_hours: 168 },
      true,
    );
  });

  it('renders overview charts fed by real timeseries points', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    mocks.fetchMonitoringTimeseries.mockResolvedValue(TS_WITH_DATA);
    renderPage();
    // 总览四张核心趋势：一图一量纲（好评率与空召回极性相反，分图呈现）。
    expect(await screen.findByText('检索次数趋势')).toBeTruthy();
    expect(screen.getByText('空召回率趋势')).toBeTruthy();
    expect(screen.getByText('好评率趋势')).toBeTruthy();
    expect(screen.getByText('响应延迟趋势')).toBeTruthy();
  });

  it('shows hits trend on conversion tab', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    mocks.fetchMonitoringTimeseries.mockResolvedValue(TS_WITH_DATA);
    renderPage();
    await openTab('conversion');
    expect(await screen.findByText('平均命中趋势')).toBeTruthy();
    // 平均命中数来自后端聚合，不再是恒 "—" 占位（面板内含图表刻度，用文本包含断言）。
    const hitsPanel = screen.getByTestId('chart-hits-panel');
    expect(hitsPanel.textContent).toContain('3.5');
    // 转化漏斗同屏：总览 → 有命中 → 已评价 → 好评。
    expect(screen.getByText('检索转化漏斗')).toBeTruthy();
  });

  it('shows feedback stats and review queue on feedback tab', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    renderPage();
    await openTab('feedback');
    // 好评/差评计数限定在反馈区块内，避免与其他数字撞文本。
    const feedback = await screen.findByTestId('feedback-section');
    expect(within(feedback).getByText('18')).toBeTruthy();
    expect(within(feedback).getByText('2')).toBeTruthy();
    expect(await screen.findByText('暂无待审差评')).toBeTruthy();
  });

  it('renders health score card with composite score', async () => {
    mocks.fetchMonitoringSummary.mockResolvedValue(HEALTHY);
    renderPage();
    expect(await screen.findByTestId('health-score-card')).toBeTruthy();
    // HEALTHY fixture → 检索93/延迟92/满意度100 加权 ≈ 96。
    expect(screen.getByTestId('health-score-card').textContent).toContain(
      '检索',
    );
    expect(screen.getByTestId('health-factor-satisfaction')).toBeTruthy();
  });

  it('shows pareto and top-queries sections on diagnosis tab', async () => {
    mocks.fetchRootCauses.mockResolvedValue(ROOT_CAUSES_DATA);
    mocks.fetchTopQueries.mockResolvedValue(TOPQ_EMPTY_DATA);
    renderPage();
    await openTab('diagnosis');
    expect(await screen.findByText('差评根因帕累托')).toBeTruthy();
    expect(await screen.findByTestId('topq-row-0')).toBeTruthy();
    expect(screen.getByTestId('topq-list').textContent).toContain('gap query');
  });

  it('switches top-queries tab and refetches by kind', async () => {
    renderPage();
    await openTab('diagnosis');
    fireEvent.click(await screen.findByTestId('topq-tab-slow'));
    expect(mocks.fetchTopQueries).toHaveBeenCalledWith({
      window_hours: 24,
      since: undefined,
      until: undefined,
      kind: 'slow',
      limit: 10,
    });
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

  it('shows error state with retry when either request fails', async () => {
    mocks.fetchMonitoringTimeseries.mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByText('监控数据加载失败')).toBeTruthy();
    mocks.fetchMonitoringSummary.mockResolvedValue(EMPTY);
    mocks.fetchMonitoringTimeseries.mockResolvedValue(EMPTY_TS);
    fireEvent.click(screen.getByTestId('monitoring-retry'));
    expect(await screen.findByText('当前无告警')).toBeTruthy();
    expect(mocks.fetchMonitoringSummary).toHaveBeenCalledTimes(2);
  });

  it('deep-links to a non-default tab via ?tab= param', async () => {
    mocks.fetchRootCauses.mockResolvedValue(ROOT_CAUSES_DATA);
    renderMonitorAt(['/?tab=diagnosis']);
    expect(await screen.findByText('差评根因帕累托')).toBeTruthy();
    // 非默认面板不挂载，ECharts 实例只在激活 Tab 内创建。
    expect(screen.queryByTestId('retrieval-section')).toBeNull();
  });

  it('falls back to overview on invalid ?tab= param', async () => {
    renderMonitorAt(['/?tab=unknown']);
    expect(await screen.findByTestId('retrieval-section')).toBeTruthy();
    expect(screen.queryByTestId('monitoring-tab-overview')!.getAttribute('aria-selected')).toBe('true');
  });

  it('syncs tab switches back to the URL search params', async () => {
    let lastSearch = '';
    renderMonitorAt(['/'], (s) => {
      lastSearch = s;
    });
    await screen.findByTestId('retrieval-section');
    await openTab('conversion');
    expect(lastSearch).toBe('?tab=conversion');
    await openTab('overview');
    expect(lastSearch).toBe('');
  });
});
