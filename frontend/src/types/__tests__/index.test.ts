import { describe, it, expect } from 'vitest';
import { getAgentInfo } from '@/types/index';
import type { AgentConfig } from '@/types/index';

describe('getAgentInfo', { tags: ['unit'] }, () => {
  const agents: AgentConfig[] = [
    {
      id: '1',
      name: '产品经理',
      role_identifier: 'pm',
      system_prompt: '分析需求',
      model: null,
      temperature: null,
      order: 1,
      is_active: true,
      is_approver: false,
      icon: '📋',
      created_at: null,
    },
    {
      id: '2',
      name: '程序员',
      role_identifier: 'dev',
      system_prompt: '写代码',
      model: 'gpt-4',
      temperature: 0.5,
      order: 2,
      is_active: true,
      is_approver: false,
      icon: '💻',
      created_at: null,
    },
    {
      id: '3',
      name: '测试工程师',
      role_identifier: 'qa',
      system_prompt: '做测试',
      model: null,
      temperature: null,
      order: 3,
      is_active: false,
      is_approver: true,
      icon: '🧪',
      created_at: null,
    },
  ];

  it('找到匹配角色时返回对应图标和名称', () => {
    const info = getAgentInfo(agents, 'pm');
    expect(info).toEqual({ icon: '📋', label: '产品经理', color: expect.any(String) });
  });

  it('未找到角色时返回默认值', () => {
    const info = getAgentInfo(agents, 'unknown_role');
    expect(info).toEqual({ icon: '◆', label: 'unknown_role', color: '#666' });
  });

  it('代理列表为空时返回默认值', () => {
    const info = getAgentInfo([], 'pm');
    expect(info).toEqual({ icon: '◆', label: 'pm', color: '#666' });
  });

  it('返回的颜色是合法的 hex 格式', () => {
    const info = getAgentInfo(agents, 'pm');
    expect(info.color).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  it('同一角色多次调用返回相同颜色（确定性）', () => {
    const c1 = getAgentInfo(agents, 'pm').color;
    const c2 = getAgentInfo(agents, 'pm').color;
    expect(c1).toBe(c2);
  });

  it('不同角色可能返回不同颜色', () => {
    const colors = new Set(['pm', 'dev', 'qa'].map((r) => getAgentInfo(agents, r).color));
    expect(colors.size).toBeGreaterThan(1);
  });

  it('空角色字符串不崩溃', () => {
    expect(() => getAgentInfo(agents, '')).not.toThrow();
    const info = getAgentInfo(agents, '');
    expect(info.icon).toBe('◆');
  });

  it('长角色字符串不崩溃', () => {
    const long = 'a'.repeat(1000);
    expect(() => getAgentInfo(agents, long)).not.toThrow();
    const info = getAgentInfo(agents, long);
    expect(info.color).toBe('#666');
  });

  it('返回的颜色在预定义调色板范围内', () => {
    const ROLE_COLORS = ['#4A90D9', '#00C853', '#FF6D00', '#9C27B0', '#00BCD4', '#FF5722', '#607D8B', '#E91E63'];
    for (const a of agents) {
      const info = getAgentInfo(agents, a.role_identifier);
      expect(ROLE_COLORS).toContain(info.color);
    }
  });
});
