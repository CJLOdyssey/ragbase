import type { TimeRangeQuery } from '../../../types/monitoring';
import LatencyHeatmap from '../LatencyHeatmap';
import LatencyScatter from '../LatencyScatter';
import RootCausePareto from '../RootCausePareto';
import TopQueriesTable from '../TopQueriesTable';

interface Props {
  timeQuery: TimeRangeQuery;
}

/** 根因诊断 Tab：回答"问题出在哪"——差评根因帕累托 + 问题查询 Top 10 + 延迟热力图 + 散点图。 */
export default function DiagnosisPanel({ timeQuery }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-stretch">
      <RootCausePareto timeQuery={timeQuery} />
      <TopQueriesTable timeQuery={timeQuery} />
      <LatencyHeatmap timeQuery={timeQuery} />
      <LatencyScatter timeQuery={timeQuery} />
    </div>
  );
}
