import type { ChatMessage, ProjectRun } from '../types';

// 分支树：按 parent_run_id 组树，返回目标 run（缺省 = 最新 run）的父链路径（根在前）
export function buildRunPath(
  runs: ProjectRun[],
  fromRunId?: string | null,
): {
  path: ProjectRun[];
  active: string | null;
} {
  const byId = new Map(runs.map((r) => [r.id, r]));
  const latest = runs.reduce(
    (a, b) =>
      (b.created_at ?? '').localeCompare(a.created_at ?? '') > 0 ? b : a,
    runs[0],
  );
  const start = fromRunId && byId.has(fromRunId) ? byId.get(fromRunId) : latest;
  const path: ProjectRun[] = [];
  const seen = new Set<string>();
  let cur: ProjectRun | undefined = start;
  while (cur && !seen.has(cur.id)) {
    seen.add(cur.id);
    path.unshift(cur);
    cur = cur.parent_run_id ? byId.get(cur.parent_run_id) : undefined;
  }
  return { path, active: start?.id ?? latest?.id ?? null };
}

// 分支完整路径：目标 run 的父链（根在前）+ 主子孙链（每次取子分支，优先
// 选非当前视图所在分支，全部都在当前分支则取最新）。切分支后显示该分支的
// 全部消息，后续轮次跟随目标分支。
export function buildBranchPath(
  runs: ProjectRun[],
  fromRunId: string,
  excludeRunIds: Set<string>,
): ProjectRun[] {
  const { path: parentPath } = buildRunPath(runs, fromRunId);
  const byParent = new Map<string, ProjectRun[]>();
  for (const r of runs) {
    const p = r.parent_run_id;
    if (!p) continue;
    const list = byParent.get(p);
    if (list) list.push(r);
    else byParent.set(p, [r]);
  }
  const tail: ProjectRun[] = [];
  const seen = new Set<string>(parentPath.map((r) => r.id));
  let cur: string | null = fromRunId;
  while (cur) {
    const kids: ProjectRun[] = (byParent.get(cur) ?? [])
      .filter((k) => !seen.has(k.id))
      .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
    const next: ProjectRun | undefined =
      kids.find((k) => !excludeRunIds.has(k.id)) ?? kids[0];
    if (!next) break;
    tail.push(next);
    seen.add(next.id);
    cur = next.id;
  }
  return [...parentPath, ...tail];
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
// 用户问题的不同回答（requirement 相同的 run 组，重新生成链），也是分支
// （与用户消息 1:N），切换走分支加载（父链 + 子孙链）。模型消息带
// userMsgId（归一化到用户消息）。
function attachBranchVersions(
  loaded: ChatMessage[],
  uIdx: number,
  branchGroup: ProjectRun[],
  runId: string,
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
      answerVersions: answerGroup.map((s) => s.requirement),
      answerRunIds: answerGroup.map((s) => s.id),
      currentAnswerVersion: answerGroup.findIndex((s) => s.id === runId),
      userMsgId,
    };
  }
}

// 路径 turns：平铺消息 + 分支点版本映射（userVersions/answerVersions）。
// runs 为会话完整 run 集，用于计算平行兄弟分支（跨分支切换入口）。
export function buildPathTurns(
  path: ProjectRun[],
  runs: ProjectRun[],
): ChatMessage[] {
  const byParent = buildByParent(runs);
  const loaded: ChatMessage[] = [];
  for (let i = 0; i < path.length; i++) {
    const run = path[i];
    for (const m of run.messages ?? []) {
      loaded.push({
        ...m,
        runId: run.id,
        parentRunId: run.parent_run_id ?? null,
        // user 消息挂 run 绑定的附件（下载入口；内容已由后端注入模型）
        ...(m.role === 'user' && run.attachments
          ? { attachments: run.attachments }
          : {}),
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
        attachBranchVersions(loaded, uIdx, branchGroup, run.id);
      }
    }
  }
  return loaded;
}
