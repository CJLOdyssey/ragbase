import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../instance', () => ({ default: mockApi }));

import { submitRequirement, resumeRun } from '../runs';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('submitRequirement', { tags: ['unit'] }, () => {
  it('calls POST /runs with requirement only', async () => {
    mockApi.post.mockResolvedValue({ data: { run_id: 'r1', status: 'queued' } });

    const result = await submitRequirement('build a website');

    expect(mockApi.post).toHaveBeenCalledWith('/runs', {
      requirement: 'build a website',
      session_id: undefined,
      key_id: undefined,
      model: undefined,
      agent_id: undefined,
      team_id: undefined,
    });
    expect(result).toEqual({ run_id: 'r1', status: 'queued' });
  });

  it('passes all optional params', async () => {
    mockApi.post.mockResolvedValue({ data: { run_id: 'r1', status: 'queued', session_id: 's1' } });

    const result = await submitRequirement('req', 's1', 'k1', 'gpt-4', 'a1', 't1');

    expect(mockApi.post).toHaveBeenCalledWith('/runs', {
      requirement: 'req',
      session_id: 's1',
      key_id: 'k1',
      model: 'gpt-4',
      agent_id: 'a1',
      team_id: 't1',
    });
    expect(result).toEqual({ run_id: 'r1', status: 'queued', session_id: 's1' });
  });
});

describe('resumeRun', { tags: ['unit'] }, () => {
  it('calls POST /runs/complete with content', async () => {
    mockApi.post.mockResolvedValue({ data: { run_id: 'r2', status: 'completed' } });

    const result = await resumeRun('continue generation');

    expect(mockApi.post).toHaveBeenCalledWith('/runs/complete', {
      content: 'continue generation',
      session_id: undefined,
      thinking: undefined,
    });
    expect(result).toEqual({ run_id: 'r2', status: 'completed' });
  });

  it('passes optional thinking and session_id', async () => {
    mockApi.post.mockResolvedValue({ data: { run_id: 'r2', status: 'completed' } });

    await resumeRun('continue', 's1', 'some thinking');

    expect(mockApi.post).toHaveBeenCalledWith('/runs/complete', {
      content: 'continue',
      session_id: 's1',
      thinking: 'some thinking',
    });
  });
});
