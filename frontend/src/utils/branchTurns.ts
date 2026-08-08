import type { ChatMessage, ProjectRun } from '../types';

export interface LoadedTurns {
  loaded: ChatMessage[];
  runTurns: Record<string, { content: string; thinking: string }>;
}

export function buildByParent(runs: ProjectRun[]): Map<string, ProjectRun[]> {
  const byParent = new Map<string, ProjectRun[]>();
  for (const r of runs) {
    // 根 run（parent=null）也入表（key=''）：多个根 = 根级兄弟分支
    // （如根 turn 的重新生成），是合法的分支点。
    const p = r.parent_run_id ?? '';
    const list = byParent.get(p);
    if (list) list.push(r);
    else byParent.set(p, [r]);
  }
  return byParent;
}

// 分支点版本挂载：user 消息 = 全部分支（切分支）；配对的模型消息 = 同一
// 用户问题的不同回答（requirement 相同的 run 组，重新生成链），本地切换。
// 模型消息带 userMsgId，切换分页时不联动用户消息（同一问题，内容不变）。
function attachBranchVersions(
  loaded: ChatMessage[],
  uIdx: number,
  branchGroup: ProjectRun[],
  runId: string,
  runTurns: Record<string, { content: string; thinking: string }>,
): void {
  const userMsg = loaded[uIdx];
  const userMsgId = userMsg.id;
  // 用户版本器 = unique 文本分支（编辑/变体）：同文本的重新生成兄弟折叠进
  // 模型答案分页（answerGroup），不在用户版本器重复出现（纯重新生成链
  // unique 只剩 1 项 → 不挂用户版本器，模型分页承担）。切换目标 = 该文本
  // 在分支组中第一个 run（原始分支）。
  const uniqueVersions: { req: string; runId: string }[] = [];
  for (const s of branchGroup) {
    if (!uniqueVersions.some((x) => x.req === s.requirement)) {
      uniqueVersions.push({ req: s.requirement, runId: s.id });
    }
  }
  if (uniqueVersions.length > 1) {
    loaded[uIdx] = {
      ...userMsg,
      userVersions: uniqueVersions.map((x) => x.req),
      versionRunIds: uniqueVersions.map((x) => x.runId),
      currentUserVersion: uniqueVersions.findIndex(
        (x) => x.req === userMsg.content,
      ),
    };
  }
  const aIdx = loaded.findIndex(
    (m, i) => i > uIdx && m.runId === runId && m.role !== 'user',
  );
  if (aIdx < 0) return;
  const cur = branchGroup.find((s) => s.id === runId);
  const answerGroup = cur
    ? branchGroup.filter((s) => s.requirement === cur.requirement)
    : [];
  if (answerGroup.length > 1) {
    loaded[aIdx] = {
      ...loaded[aIdx],
      userVersions: answerGroup.map((s) => s.requirement),
      versionRunIds: answerGroup.map((s) => s.id),
      currentUserVersion: answerGroup.findIndex((s) => s.id === runId),
      userMsgId,
    };
  }
  // 答案组所有 run 的 agent turn 进 runTurns：模型消息分页本地切换，
  // 无需整分支加载。
  for (const r of answerGroup) {
    const am = (r.messages ?? []).find((m) => m.role !== 'user');
    if (am) {
      runTurns[r.id] = {
        content: am.content ?? '',
        thinking: am.thinking ?? '',
      };
    }
  }
}

// 路径 turns：平铺消息 + runTurns（runId → agent turn）+ 版本映射（versionRunIds）
// runs 为会话完整 run 集，用于计算平行兄弟分支（跨分支切换入口）。
export function buildPathTurns(
  path: ProjectRun[],
  runs: ProjectRun[],
): LoadedTurns {
  const byParent = buildByParent(runs);
  const loaded: ChatMessage[] = [];
  const runTurns: Record<string, { content: string; thinking: string }> = {};
  for (let i = 0; i < path.length; i++) {
    const run = path[i];
    for (const m of run.messages ?? []) {
      loaded.push({
        ...m,
        runId: run.id,
        parentRunId: run.parent_run_id ?? null,
      });
    }
    // 版本计数：user 消息带分支点兄弟组（run 层）。分支判定只看 branchGroup
    // 是否有兄弟 — 不依赖 requirement_versions（仅编辑链场景非空；根 run 的
    // 重新生成兄弟 parent=null → requirement_versions=None，但仍是分支点）。
    // 线性追问 turn 的 parent 只有一个子 → branchGroup.length=1 → 不挂载。
    const uIdx = loaded.findIndex(
      (m) => m.runId === run.id && m.role === 'user',
    );
    if (uIdx >= 0) {
      const branchGroup = (byParent.get(run.parent_run_id ?? '') ?? []).sort(
        (a, b) => (a.created_at ?? '').localeCompare(b.created_at ?? ''),
      );
      if (branchGroup.length > 1) {
        attachBranchVersions(loaded, uIdx, branchGroup, run.id, runTurns);
      }
    }
    // runTurns：runId → agent turn（分页切换时模型消息联动）
    const agentMsg = (run.messages ?? []).find((m) => m.role !== 'user');
    if (agentMsg) {
      runTurns[run.id] = {
        content: agentMsg.content ?? '',
        thinking: agentMsg.thinking ?? '',
      };
    }
  }
  return { loaded, runTurns };
}
