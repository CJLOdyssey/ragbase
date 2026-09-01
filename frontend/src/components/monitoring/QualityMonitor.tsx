import type { ComponentType } from 'react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import type { TimeRangeQuery } from '../../types/monitoring';
import MonitoringTabs from './MonitoringTabs';
import OverviewPanel from './panels/OverviewPanel';
import ConversionPanel from './panels/ConversionPanel';
import DiagnosisPanel from './panels/DiagnosisPanel';
import FeedbackPanel from './panels/FeedbackPanel';
import {
  useMonitoringTab,
  type MonitoringTabKey,
} from './useMonitoringTab';

const WINDOWS = [
  { hours: 24, key: 'monitoring.windowDay' },
  { hours: 24 * 7, key: 'monitoring.windowWeek' },
  { hours: 24 * 30, key: 'monitoring.windowMonth' },
  // 0 = all time — the backend builds a bounded grid for it.
  { hours: 0, key: 'monitoring.windowAll' },
] as const;

/** 自定义范围激活时下发给全部子面板的统一时间参数。 */
function buildTimeQuery(
  range: [Dayjs, Dayjs] | null,
  windowHours: number,
): TimeRangeQuery {
  if (range) {
    return {
      window_hours: 0,
      since: range[0].toISOString(),
      until: range[1].toISOString(),
    };
  }
  return { window_hours: windowHours };
}

interface PanelProps {
  timeQuery: TimeRangeQuery;
}

const PANELS: Record<MonitoringTabKey, ComponentType<PanelProps>> = {
  overview: OverviewPanel,
  conversion: ConversionPanel,
  diagnosis: DiagnosisPanel,
  feedback: FeedbackPanel,
};

/**
 * 质量监控壳层：只负责共享时间控件与 Tab 导航；
 * 各 Tab 的数据获取与图表渲染下沉到 panels/ 下自治面板。
 */
export default function QualityMonitor() {
  const { t } = useTranslation();
  const [windowHours, setWindowHours] = useState(24);
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null);
  const timeQuery = useMemo(
    () => buildTimeQuery(range, windowHours),
    [range, windowHours],
  );
  const { tab, setTab } = useMonitoringTab();

  const ActivePanel = PANELS[tab];

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)]">
      <div className="flex flex-col gap-2 px-4 py-4 border-b border-[var(--color-border)] sm:px-6">
        <h1 className="text-lg font-semibold text-[var(--color-text-primary)] m-0">
          {t('monitoring.title')}
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          <DatePicker.RangePicker
            popupClassName="mobile-picker"
            showTime={{ format: 'HH:mm' }}
            format="YYYY-MM-DD HH:mm"
            value={range}
            allowClear
            disabledDate={(d) => d.isAfter(dayjs(), 'day')}
            onChange={(v) =>
              setRange(
                v && v[0] && v[1] ? ([v[0], v[1]] as [Dayjs, Dayjs]) : null,
              )
            }
            placeholder={[
              t('monitoring.rangeStart'),
              t('monitoring.rangeEnd'),
            ]}
            data-testid="custom-range"
          />
          <div className="hidden md:block flex-1" />
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-1 shrink-0">
            {WINDOWS.map((w) => (
              <button
                key={w.hours}
                className={`px-2 py-1.5 rounded-md text-xs cursor-pointer border-none transition-colors duration-150 sm:px-3 sm:text-sm ${
                  !range && windowHours === w.hours
                    ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)]'
                    : 'bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                }`}
                onClick={() => {
                  setRange(null);
                  setWindowHours(w.hours);
                }}
                data-testid={`window-${w.hours}`}
              >
                {t(w.key)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-6">
        <div className="flex flex-col gap-4">
          <MonitoringTabs tab={tab} onChange={setTab} />
          <ActivePanel timeQuery={timeQuery} />
        </div>
      </div>
    </div>
  );
}
