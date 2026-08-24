import { useEffect, useRef, useState } from 'react';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Checkbox, DatePicker, InputNumber, Tag } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { FileSearch } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import {
  getRetrievalStats,
  listRetrievalLogs,
} from '../../api/client/retrievalLogs';
import LatencyBar from './LatencyBar';
import LogsPagination from './LogsPagination';
import RetrievalStatsCharts from './RetrievalStatsCharts';
import RetrievalTable from './RetrievalTable';

const HOUR_OPTIONS = [
  { hours: 0, key: 'monitoring.windowAll' },
  { hours: 24, key: 'monitoring.windowDay' },
  { hours: 72, key: 'retrievalLogs.last72h' },
  { hours: 168, key: 'monitoring.windowWeek' },
] as const;

/**
 * 双层时间控件（对齐质量监控页惯例）：预设窗口按钮组 + 自定义绝对范围。
 * 自定义范围优先于预设窗口；URL 为唯一事实源，刷新/分享可还原。
 */
function TimeControls({
  sinceHours,
  range,
}: {
  sinceHours: number;
  range: [Dayjs, Dayjs] | null;
}) {
  const { t } = useTranslation();
  const [, setSearchParams] = useSearchParams();

  const writeParams = (mutate: (next: URLSearchParams) => void) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        mutate(next);
        return next;
      },
      { replace: true },
    );
  };

  return (
    <div className="flex items-center gap-2">
      <DatePicker.RangePicker
        showTime={{ format: 'HH:mm' }}
        format="YYYY-MM-DD HH:mm"
        value={range}
        allowClear
        disabledDate={(d) => d.isAfter(dayjs(), 'day')}
        onChange={(v) =>
          writeParams((next) => {
            if (v && v[0] && v[1]) {
              next.set('since', v[0].toISOString());
              next.set('until', v[1].toISOString());
              next.delete('hours');
            } else {
              next.delete('since');
              next.delete('until');
            }
          })
        }
        placeholder={[t('monitoring.rangeStart'), t('monitoring.rangeEnd')]}
        data-testid="logs-custom-range"
      />
      <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-1">
        {HOUR_OPTIONS.map((w) => (
          <button
            key={w.hours}
            className={`px-3 py-1.5 rounded-md text-sm cursor-pointer border-none transition-colors duration-150 ${
              !range && sinceHours === w.hours
                ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)]'
                : 'bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            }`}
            onClick={() =>
              writeParams((next) => {
                next.delete('since');
                next.delete('until');
                if (w.hours > 0) next.set('hours', String(w.hours));
                else next.delete('hours');
              })
            }
            data-testid={`window-${w.hours}`}
          >
            {t(w.key)}
          </button>
        ))}
      </div>
    </div>
  );
}

/** 筛选工具栏 —— 全部条件自持 URL 同步；页码重置由父组件的参数派生逻辑处理。 */
function LogsToolbar({
  emptyOnly,
  maxLatency,
}: {
  emptyOnly: boolean;
  maxLatency: string;
}) {
  const { t } = useTranslation();
  const [, setSearchParams] = useSearchParams();

  const writeParams = (mutate: (next: URLSearchParams) => void) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        mutate(next);
        return next;
      },
      { replace: true },
    );
  };

  // 输入框绑定本地草稿态：URL 逐键写入不再打断 rc-input-number 的内部缓冲
  // （直接受控于 URL 时首键重渲染会吞掉后续按键，500 只剩 5）。
  // lastSynced 去重自身写入，仅外部变更（返回/分享链接）才回填草稿。
  const [latencyDraft, setLatencyDraft] = useState(maxLatency);
  const lastSyncedRef = useRef(maxLatency);

  useEffect(() => {
    if (maxLatency !== lastSyncedRef.current) {
      lastSyncedRef.current = maxLatency;
      setLatencyDraft(maxLatency);
    }
  }, [maxLatency]);

  const handleLatencyChange = (v: number | null) => {
    const next = v == null ? '' : String(v);
    lastSyncedRef.current = next;
    setLatencyDraft(next);
    writeParams((p) => {
      if (next) p.set('max_latency', next);
      else p.delete('max_latency');
    });
  };

  return (
    <div className="flex items-center gap-4 mb-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-2.5">
      <Checkbox
        checked={emptyOnly}
        onChange={(e) => {
          writeParams((next) => {
            if (e.target.checked) next.set('empty', '1');
            else next.delete('empty');
          });
        }}
      >
        {t('retrievalLogs.emptyOnly')}
      </Checkbox>
      <div className="w-px h-4 bg-[var(--color-border)]" />
      <div className="flex items-center gap-2">
        <span className="text-sm text-[var(--color-text-secondary)]">
          {t('retrievalLogs.maxLatency')}
        </span>
        <InputNumber
          value={latencyDraft ? Number(latencyDraft) : null}
          placeholder="0"
          min={0}
          onChange={handleLatencyChange}
          className="w-24"
        />
        <span className="text-xs text-[var(--color-text-muted)] font-mono">
          ms
        </span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        {maxLatency && (
          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
            {t('retrievalLogs.latencyFilterTag', { maxLatency })}
          </Tag>
        )}
      </div>
    </div>
  );
}

/** URL 参数 → 时间窗口解析（自定义绝对范围优先于 hours 预设）。 */
function resolveTimeWindow(searchParams: URLSearchParams): {
  range: [Dayjs, Dayjs] | null;
  sinceHours: number;
  apiWindow: { since: string; until: string } | { since_hours?: number };
  timeKey: string;
} {
  const sinceParam = searchParams.get('since');
  const untilParam = searchParams.get('until');
  const range: [Dayjs, Dayjs] | null =
    sinceParam && untilParam ? [dayjs(sinceParam), dayjs(untilParam)] : null;
  const sinceHours = Number(searchParams.get('hours')) || 0;
  const apiWindow = range
    ? { since: range[0].toISOString(), until: range[1].toISOString() }
    : { since_hours: sinceHours || undefined };
  const timeKey = range
    ? `range-${sinceParam}-${untilParam}`
    : `hours-${sinceHours}`;
  return { range, sinceHours, apiWindow, timeKey };
}

/** 趋势图标题用窗口标签：自定义区间显示起止，预设窗口显示文案。 */
function resolveRangeLabel(
  t: (key: string) => string,
  range: [Dayjs, Dayjs] | null,
  sinceHours: number,
): string {
  if (range) {
    return `${range[0].format('MM-DD HH:mm')} ~ ${range[1].format('MM-DD HH:mm')}`;
  }
  return t(
    HOUR_OPTIONS.find((w) => w.hours === sinceHours)?.key ??
      'monitoring.windowAll',
  );
}

export default function RetrievalLogPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  // 下钻契约：监控页 KPI 卡通过 ?hours=&empty= 携带过滤条件直达；
  // 自定义范围 ?since=&until=（ISO）优先；URL 为唯一事实源。
  const { range, sinceHours, apiWindow, timeKey } =
    resolveTimeWindow(searchParams);
  const emptyOnly = searchParams.get('empty') === '1';
  const maxLatency = searchParams.get('max_latency') ?? '';
  const paramsKey = `${timeKey}|${emptyOnly}|${maxLatency}`;

  const [page, setPage] = useState(1);
  const [prevParamsKey, setPrevParamsKey] = useState(paramsKey);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const pageSize = 20;

  if (prevParamsKey !== paramsKey) {
    setPrevParamsKey(paramsKey);
    if (page !== 1) setPage(1);
  }

  // placeholderData：换筛选时保留旧内容渲染，工具栏不卸载、输入焦点不丢。
  const { data, isLoading } = useQuery({
    queryKey: ['retrieval-logs', page, emptyOnly, maxLatency, timeKey],
    queryFn: () =>
      listRetrievalLogs({
        page,
        page_size: pageSize,
        empty_only: emptyOnly || undefined,
        max_latency_ms: maxLatency ? Number(maxLatency) : undefined,
        ...apiWindow,
      }),
    placeholderData: keepPreviousData,
  });

  const { data: stats } = useQuery({
    queryKey: ['retrieval-stats', emptyOnly, maxLatency, timeKey],
    queryFn: () =>
      getRetrievalStats({
        empty_only: emptyOnly || undefined,
        max_latency_ms: maxLatency ? Number(maxLatency) : undefined,
        ...apiWindow,
      }),
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const totalPages = data ? Math.ceil(total / pageSize) : 0;
  const items = data?.items ?? [];
  const rangeLabel = resolveRangeLabel(t, range, sinceHours);

  const toggleRow = (id: string) =>
    setExpandedId((cur) => (cur === id ? null : id));

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <div className="flex items-center justify-between gap-4 px-8 py-5 border-b border-[var(--color-border)]">
        <div>
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
            {t('retrievalLogs.title')}
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1 m-0">
            {t('retrievalLogs.subtitle')}
          </p>
        </div>
        <TimeControls sinceHours={sinceHours} range={range} />
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 px-8 py-6">
        {!isLoading && (
          <LogsToolbar emptyOnly={emptyOnly} maxLatency={maxLatency} />
        )}
        {isLoading ? (
          <LoadingState centered />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FileSearch size={24} />}
            title={t('retrievalLogs.noLogs')}
            description={t('retrievalLogs.noLogsDesc')}
            centered
          />
        ) : (
          <>
            {stats && (
              <RetrievalStatsCharts stats={stats} rangeLabel={rangeLabel} />
            )}

            <LatencyBar items={items} />

            <RetrievalTable
              items={items}
              expandedId={expandedId}
              onToggle={toggleRow}
            />
          </>
        )}
        {!isLoading && (
          <LogsPagination
            page={page}
            totalPages={totalPages}
            total={total}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  );
}
