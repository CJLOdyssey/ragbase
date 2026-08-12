import { buildBranchPath, buildByParent, buildRunPath } from '../branchTurns';
import { describe, expect, it } from 'vitest';
import type { ProjectRun } from '../../types';

function makeRun(
  id: string,
  requirement: string,
  parent_run_id: string | null,
  created_at: string,
): ProjectRun {
  return {
    id,
    session_id: 'sess-1',
    requirement,
    pm_document: '',
    code: '',
    review: '',
    approved: false,
    status: 'completed',
    created_at,
    updated_at: created_at,
    parent_run_id,
    requirement_versions: null,
  };
}

describe('buildRunPath', { tags: ['unit'] }, () => {
  it('builds root-first parent chain for the latest run by default', () => {
    const runs = [
      makeRun('r1', 'q1', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-08-08T00:01:00Z'),
      makeRun('r3', 'q3', 'r2', '2026-08-08T00:02:00Z'),
    ];
    const { path, active } = buildRunPath(runs);
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2', 'r3']);
    expect(active).toBe('r3');
  });

  it('starts from fromRunId when it exists in the map', () => {
    const runs = [
      makeRun('r1', 'q1', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-08-08T00:01:00Z'),
      makeRun('r3', 'q3', 'r2', '2026-08-08T00:02:00Z'),
    ];
    const { path, active } = buildRunPath(runs, 'r2');
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2']);
    expect(active).toBe('r2');
  });

  it('falls back to latest when fromRunId is unknown or falsy', () => {
    const runs = [
      makeRun('r1', 'q1', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-08-08T00:01:00Z'),
    ];
    expect(buildRunPath(runs, 'missing').active).toBe('r2');
    expect(buildRunPath(runs, '').active).toBe('r2');
    expect(buildRunPath(runs, null).active).toBe('r2');
  });

  it('returns empty path and null active for empty runs', () => {
    expect(buildRunPath([])).toEqual({ path: [], active: null });
  });

  it('breaks cycles with the seen set instead of looping forever', () => {
    const runs = [
      makeRun('r1', 'q1', 'r2', '2026-08-08T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-08-08T00:01:00Z'),
    ];
    const { path } = buildRunPath(runs, 'r1');
    // 环形父链：seen 集合保证终止；路径只包含 2 个 run（根在前）
    expect(path.map((r) => r.id)).toEqual(['r2', 'r1']);
  });
});

describe('buildByParent', { tags: ['unit'] }, () => {
  it('groups children under their parent id and roots under empty key', () => {
    const runs = [
      makeRun('r1', 'q1', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', 'q2', null, '2026-08-08T00:01:00Z'),
      makeRun('r3', 'q3', 'r1', '2026-08-08T00:02:00Z'),
    ];
    const byParent = buildByParent(runs);
    expect(byParent.get('')!.map((r) => r.id)).toEqual(['r1', 'r2']);
    expect(byParent.get('r1')!.map((r) => r.id)).toEqual(['r3']);
  });
});

describe('buildBranchPath', { tags: ['unit'] }, () => {
  const runs = [
    makeRun('r1', 'q1', null, '2026-08-08T00:00:00Z'),
    makeRun('r2', 'q2', 'r1', '2026-08-08T00:01:00Z'),
    makeRun('r3', 'q3', 'r1', '2026-08-08T00:02:00Z'),
    makeRun('r4', 'q4', 'r3', '2026-08-08T00:03:00Z'),
  ];

  it('returns parent chain plus descendant tail picking the non-excluded branch', () => {
    // 目标 r2：父链 [r1,r2]；从 r2 无子 → tail 空
    expect(buildBranchPath(runs, 'r2', new Set()).map((r) => r.id)).toEqual([
      'r1',
      'r2',
    ]);
    // 目标 r1：父链 [r1]；子分支 r3 非当前 → 选 r3，再选 r3 的子 r4
    expect(buildBranchPath(runs, 'r1', new Set()).map((r) => r.id)).toEqual([
      'r1',
      'r3',
      'r4',
    ]);
  });

  it('excludes runs already in the current view (excludeRunIds)', () => {
    // 当前视图含 r2/r3 分支 → 从 r1 下行时排除 r3，选 r2
    const exclude = new Set(['r3', 'r4']);
    expect(buildBranchPath(runs, 'r1', exclude).map((r) => r.id)).toEqual([
      'r1',
      'r2',
    ]);
  });

  it('falls back to the newest child when all are excluded', () => {
    const exclude = new Set(['r2', 'r3', 'r4']);
    // r1 的所有子分支都在当前视图 → 退回取最新子（created_at 排序）
    expect(buildBranchPath(runs, 'r1', exclude).map((r) => r.id)).toEqual([
      'r1',
      'r3',
      'r4',
    ]);
  });

  it('stops when a branch run has no unvisited children', () => {
    expect(buildBranchPath(runs, 'r4', new Set()).map((r) => r.id)).toEqual([
      'r1',
      'r3',
      'r4',
    ]);
  });
});
