import { buildPathTurns } from '../branchTurns';
import { describe, expect, it } from 'vitest';
import type { ProjectRun } from '../../types';

function makeRun(
  id: string,
  requirement: string,
  parent_run_id: string | null,
  created_at: string,
  requirement_versions: string[] | null = null,
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
    requirement_versions,
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
        thinking: `思考:${requirement}`,
        round_number: 1,
        created_at,
      },
    ],
  };
}

describe('buildPathTurns', { tags: ['unit'] }, () => {
  it('分支点：user 消息版本器 = 全部分支（切分支），模型消息无分页（单答案）', () => {
    const runs = [
      makeRun('r1', '你是什么模型', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '你知道什么是agent 吗', 'r1', '2026-08-08T00:01:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
      ]),
      makeRun('r3', '你知道什么是skill 吗', 'r1', '2026-08-08T00:02:00Z', [
        '你是什么模型',
        '你知道什么是skill 吗',
      ]),
    ];
    const { loaded, runTurns } = buildPathTurns([runs[0], runs[1]], runs);
    const agentMsg = loaded.find((m) => m.content === '你知道什么是agent 吗');
    expect(agentMsg?.userVersions).toEqual([
      '你知道什么是agent 吗',
      '你知道什么是skill 吗',
    ]);
    expect(agentMsg?.versionRunIds).toEqual(['r2', 'r3']);
    expect(agentMsg?.currentUserVersion).toBe(0);

    // 模型消息：agent 问题只有 1 个回答 → 无分页（answer 字段不挂载）
    const agentTurn = loaded.find(
      (m) => m.content === '回答:你知道什么是agent 吗',
    );
    expect(agentTurn?.answerVersions).toBeUndefined();
    expect(agentTurn?.answerRunIds).toBeUndefined();
    expect(runTurns.r2).toEqual({
      content: '回答:你知道什么是agent 吗',
      thinking: '思考:你知道什么是agent 吗',
    });
  });

  it('重新生成：模型消息分页 = 同一问题的不同回答（requirement 相同），不切分支', () => {
    const runs = [
      makeRun('r1', '你是什么模型', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '你知道什么是agent 吗', 'r1', '2026-08-08T00:01:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
      ]),
      makeRun('r3', '你知道什么是skill 吗', 'r1', '2026-08-08T00:02:00Z', [
        '你是什么模型',
        '你知道什么是skill 吗',
      ]),
      makeRun('r4', '你知道什么是skill 吗', 'r1', '2026-08-08T00:03:00Z', [
        '你是什么模型',
        '你知道什么是skill 吗',
      ]),
    ];
    const { loaded, runTurns } = buildPathTurns([runs[0], runs[3]], runs);

    // user 消息版本器 = unique 文本分支（agent / skill）：同文本的重新生成
    // 分支（r4）折叠进模型答案分页，不在用户版本器重复出现
    const userMsg = loaded.find((m) => m.content === '你知道什么是skill 吗');
    expect(userMsg?.userVersions).toEqual([
      '你知道什么是agent 吗',
      '你知道什么是skill 吗',
    ]);
    expect(userMsg?.versionRunIds).toEqual(['r2', 'r3']);
    expect(userMsg?.currentUserVersion).toBe(1);

    // 模型消息分页 = 同一问题的 2 个回答（r3 skill 原始, r4 重新生成）
    const agentTurn = loaded.find(
      (m) => m.content === '回答:你知道什么是skill 吗',
    );
    expect(agentTurn?.answerVersions).toEqual([
      '你知道什么是skill 吗',
      '你知道什么是skill 吗',
    ]);
    expect(agentTurn?.answerRunIds).toEqual(['r3', 'r4']);
    expect(agentTurn?.currentAnswerVersion).toBe(1);
    expect(agentTurn?.userMsgId).toBe(userMsg?.id);

    // runTurns 覆盖答案组全部 run → 模型分页本地切换，无需整分支加载
    expect(runTurns.r3).toEqual({
      content: '回答:你知道什么是skill 吗',
      thinking: '思考:你知道什么是skill 吗',
    });
    expect(runTurns.r4).toEqual({
      content: '回答:你知道什么是skill 吗',
      thinking: '思考:你知道什么是skill 吗',
    });
  });

  it('后续追问 turn：模型消息也无版本数据', () => {
    const runs = [
      makeRun('r1', '你是什么模型', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '你知道什么是agent 吗', 'r1', '2026-08-08T00:01:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
      ]),
      makeRun('r3', '你知道什么是skill 吗', 'r1', '2026-08-08T00:02:00Z', [
        '你是什么模型',
        '你知道什么是skill 吗',
      ]),
      makeRun('r4', 'agent出现的年份', 'r2', '2026-08-08T00:03:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
        'agent出现的年份',
      ]),
    ];
    const { loaded } = buildPathTurns([runs[0], runs[1], runs[3]], runs);
    const followUp = loaded.find((m) => m.content === 'agent出现的年份');
    expect(followUp?.userVersions).toBeUndefined();
    expect(followUp?.versionRunIds).toBeUndefined();
    expect(followUp?.currentUserVersion).toBeUndefined();
    const followUpTurn = loaded.find(
      (m) => m.content === '回答:agent出现的年份',
    );
    expect(followUpTurn?.userVersions).toBeUndefined();
    expect(followUpTurn?.userMsgId).toBeUndefined();
  });

  it('非分支点：skill 分支无后续消息', () => {
    const runs = [
      makeRun('r1', '你是什么模型', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '你知道什么是agent 吗', 'r1', '2026-08-08T00:01:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
      ]),
      makeRun('r3', '你知道什么是skill 吗', 'r1', '2026-08-08T00:02:00Z', [
        '你是什么模型',
        '你知道什么是skill 吗',
      ]),
    ];
    const { loaded } = buildPathTurns([runs[0], runs[2]], runs);
    expect(loaded.map((m) => m.content)).toEqual([
      '你是什么模型',
      '回答:你是什么模型',
      '你知道什么是skill 吗',
      '回答:你知道什么是skill 吗',
    ]);
  });

  it('根 run 重新生成（parent=null、无 requirement_versions）：用户版本器不挂（文本相同），模型分页挂载，分支判定只看兄弟组', () => {
    const runs = [
      makeRun('r1', '什么是 RAG', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '什么是 RAG', null, '2026-08-08T00:01:00Z'),
    ];
    const { loaded } = buildPathTurns([runs[1]], runs);

    // 纯重新生成链：用户版本器文本 unique 只剩 1 项 → 不挂（避免与模型
    // 答案分页重复）；模型消息分页 = 同问题的不同回答
    const userMsg = loaded.find((m) => m.role === 'user');
    expect(userMsg?.userVersions).toBeUndefined();
    expect(userMsg?.versionRunIds).toBeUndefined();

    const agentTurn = loaded.find((m) => m.role !== 'user');
    expect(agentTurn?.answerVersions).toEqual(['什么是 RAG', '什么是 RAG']);
    expect(agentTurn?.answerRunIds).toEqual(['r1', 'r2']);
    expect(agentTurn?.currentAnswerVersion).toBe(1);
    expect(agentTurn?.userMsgId).toBe(userMsg?.id);
  });

  it('runTurns：runId → agent turn 联动', () => {
    const runs = [
      makeRun('r1', '你是什么模型', null, '2026-08-08T00:00:00Z'),
      makeRun('r2', '你知道什么是agent 吗', 'r1', '2026-08-08T00:01:00Z', [
        '你是什么模型',
        '你知道什么是agent 吗',
      ]),
    ];
    const { runTurns } = buildPathTurns(runs, runs);
    expect(runTurns.r1).toEqual({
      content: '回答:你是什么模型',
      thinking: '思考:你是什么模型',
    });
    expect(runTurns.r2).toEqual({
      content: '回答:你知道什么是agent 吗',
      thinking: '思考:你知道什么是agent 吗',
    });
  });
});
