import { describe, it, expect } from 'vitest';
import { getAllAgents } from '../agentMapper';

describe('getAllAgents', { tags: ['unit'] }, () => {
  it('returns empty array for no teams', () => {
    expect(getAllAgents([])).toEqual([]);
  });

  it('flattens agents from all teams', () => {
    const teams = [
      { id: '1', name: 'Team A', agents: [{ id: 'a1', name: 'Agent1' }, { id: 'a2', name: 'Agent2' }] },
      { id: '2', name: 'Team B', agents: [{ id: 'b1', name: 'Agent3' }] },
    ];
    const result = getAllAgents(teams);
    expect(result).toHaveLength(3);
    expect(result[0].id).toBe('a1');
    expect(result[1].id).toBe('a2');
    expect(result[2].id).toBe('b1');
  });

  it('handles teams with empty agents', () => {
    const teams = [
      { id: '1', name: 'Team A', agents: [] },
    ];
    expect(getAllAgents(teams)).toEqual([]);
  });
});
