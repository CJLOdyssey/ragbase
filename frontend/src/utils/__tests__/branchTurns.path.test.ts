import {
  buildBranchPath,
  buildByParent,
  buildPathTurns,
  buildRunPath,
} from '../branchTurns';
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
    messages: [
      {
        id: `user-${id}`,
        role: 'user',
        agent_name: '我',
        content: requirement,
        round_number: 1,
        created_at,
      },
      {
        id: `agent-${id}`,
        role: 'agent',
        agent_name: 'Agent',
        content: `回答:${requirement}`,
        round_number: 1,
        created_at,
      },
    ],
  };
}

describe('buildRunPath', () => {
  const runs = [
    makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z'),
    makeRun('r2', 'q2', 'r1', '2026-01-01T00:01:00Z'),
    makeRun('r3', 'q3', 'r2', '2026-01-01T00:02:00Z'),
  ];

  it('walks the parent chain root-first', () => {
    const { path, active } = buildRunPath(runs, 'r3');
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2', 'r3']);
    expect(active).toBe('r3');
  });

  it('defaults to the latest run', () => {
    const { path, active } = buildRunPath(runs);
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2', 'r3']);
    expect(active).toBe('r3');
  });

  it('falls back to latest when fromRunId is unknown', () => {
    const { active } = buildRunPath(runs, 'ghost');
    expect(active).toBe('r3');
  });

  it('handles empty runs', () => {
    const { path, active } = buildRunPath([]);
    expect(path).toEqual([]);
    expect(active).toBeNull();
  });
});

describe('buildBranchPath', () => {
  const runs = [
    makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z'),
    makeRun('r2', 'q2', 'r1', '2026-01-01T00:01:00Z'),
    makeRun('r3', 'q3', 'r1', '2026-01-01T00:02:00Z'),
    makeRun('r4', 'q4', 'r2', '2026-01-01T00:03:00Z'),
  ];

  it('appends the main descendant chain after the parent path', () => {
    const path = buildBranchPath(runs, 'r2', new Set());
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2', 'r4']);
  });

  it('prefers a sibling not in excludeRunIds when multiple kids exist', () => {
    const branchRuns = [
      makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-01-01T00:01:00Z'),
      makeRun('r3', 'q3', 'r1', '2026-01-01T00:02:00Z'),
      makeRun('r4', 'q4', 'r2', '2026-01-01T00:03:00Z'),
      makeRun('r5', 'q5', 'r2', '2026-01-01T00:04:00Z'),
    ];
    const path = buildBranchPath(branchRuns, 'r2', new Set(['r4']));
    expect(path.map((r) => r.id)).toEqual(['r1', 'r2', 'r5']);
  });
});

describe('buildByParent', () => {
  it('groups children by parent with root runs keyed empty', () => {
    const runs = [
      makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z'),
      makeRun('r2', 'q2', 'r1', '2026-01-01T00:01:00Z'),
      makeRun('r3', 'q3', 'r1', '2026-01-01T00:02:00Z'),
    ];
    const byParent = buildByParent(runs);
    expect(byParent.get('').map((r) => r.id)).toEqual(['r1']);
    expect(byParent.get('r1').map((r) => r.id)).toEqual(['r2', 'r3']);
  });
});

describe('buildPathTurns edge cases', () => {
  it('propagates run attachments onto user messages', () => {
    const run = makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z');
    run.attachments = [{ id: 'att1', filename: 'a.pdf' }];
    const loaded = buildPathTurns([run], [run]);
    const userMsg = loaded.find((m) => m.role === 'user');
    expect(userMsg?.attachments).toEqual([{ id: 'att1', filename: 'a.pdf' }]);
    const agentMsg = loaded.find((m) => m.role !== 'user');
    expect(agentMsg?.attachments).toBeUndefined();
  });

  it('stamps runId and parentRunId on every message', () => {
    const run = makeRun('r1', 'q1', null, '2026-01-01T00:00:00Z');
    const loaded = buildPathTurns([run], [run]);
    expect(loaded.every((m) => m.runId === 'r1')).toBe(true);
    expect(loaded.every((m) => m.parentRunId === null)).toBe(true);
  });
});
