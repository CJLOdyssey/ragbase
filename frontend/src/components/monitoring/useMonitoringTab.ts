import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

export type MonitoringTabKey =
  | 'overview'
  | 'conversion'
  | 'diagnosis'
  | 'feedback';

export const DEFAULT_MONITORING_TAB: MonitoringTabKey = 'overview';

export const MONITORING_TABS: ReadonlyArray<{
  key: MonitoringTabKey;
  labelKey: string;
}> = [
  { key: 'overview', labelKey: 'monitoring.tabs.overview' },
  { key: 'conversion', labelKey: 'monitoring.tabs.conversion' },
  { key: 'diagnosis', labelKey: 'monitoring.tabs.diagnosis' },
  { key: 'feedback', labelKey: 'monitoring.tabs.feedback' },
];

const TAB_KEYS = new Set<string>(
  MONITORING_TABS.map((entry) => entry.key),
);

/**
 * 监控页 Tab 状态的唯一事实源是 URL（?tab=）：
 * 路由挂载点与工作站视图挂载点行为一致，刷新/分享可直达指定 Tab。
 * 默认 Tab 不写入参数，保持 URL 干净；非法值回退默认。
 */
export function useMonitoringTab(): {
  tab: MonitoringTabKey;
  setTab: (next: MonitoringTabKey) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();

  const raw = searchParams.get('tab');
  const tab: MonitoringTabKey =
    raw && TAB_KEYS.has(raw)
      ? (raw as MonitoringTabKey)
      : DEFAULT_MONITORING_TAB;

  const setTab = useCallback(
    (next: MonitoringTabKey) => {
      const params = new URLSearchParams(searchParams);
      if (next === DEFAULT_MONITORING_TAB) {
        params.delete('tab');
      } else {
        params.set('tab', next);
      }
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  return { tab, setTab };
}
