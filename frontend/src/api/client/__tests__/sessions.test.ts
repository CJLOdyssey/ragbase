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

import {
  listSessions,
  getSessionDetail,
  createSession,
  renameSession,
  deleteSession,
  deleteMemory,
  exportSessionMemories,
  getRun,
  listRuns,
  healthCheck,
} from '../sessions';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('listSessions', { tags: ['unit'] }, () => {
  it('calls GET /sessions with default params', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    await listSessions();

    expect(mockApi.get).toHaveBeenCalledWith('/sessions', { params: { limit: 50 } });
  });

  it('passes agent_id when provided', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    await listSessions(50, 'agent1');

    expect(mockApi.get).toHaveBeenCalledWith('/sessions', { params: { limit: 50, agent_id: 'agent1' } });
  });
});

describe('getSessionDetail', { tags: ['unit'] }, () => {
  it('calls GET /sessions/:id', async () => {
    mockApi.get.mockResolvedValue({ data: { id: 's1', title: 'Chat' } });

    const result = await getSessionDetail('s1');

    expect(mockApi.get).toHaveBeenCalledWith('/sessions/s1');
    expect(result).toEqual({ id: 's1', title: 'Chat' });
  });
});

describe('createSession', { tags: ['unit'] }, () => {
  it('calls POST /sessions with default title', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 's1', title: '新对话' } });

    const result = await createSession();

    expect(mockApi.post).toHaveBeenCalledWith('/sessions', { title: '新对话' });
    expect(result).toEqual({ id: 's1', title: '新对话' });
  });

  it('passes agent_id when provided', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 's1', title: 'Chat' } });

    await createSession('Chat', 'agent1');

    expect(mockApi.post).toHaveBeenCalledWith('/sessions', { title: 'Chat', agent_id: 'agent1' });
  });
});

describe('renameSession', { tags: ['unit'] }, () => {
  it('calls PUT /sessions/:id with title', async () => {
    mockApi.put.mockResolvedValue({});

    await renameSession('s1', 'New Title');

    expect(mockApi.put).toHaveBeenCalledWith('/sessions/s1', { title: 'New Title' });
  });
});

describe('deleteSession', { tags: ['unit'] }, () => {
  it('calls DELETE /sessions/:id', async () => {
    mockApi.delete.mockResolvedValue({});

    await deleteSession('s1');

    expect(mockApi.delete).toHaveBeenCalledWith('/sessions/s1');
  });
});

describe('deleteMemory', { tags: ['unit'] }, () => {
  it('calls DELETE /memories/:id', async () => {
    mockApi.delete.mockResolvedValue({});

    await deleteMemory('m1');

    expect(mockApi.delete).toHaveBeenCalledWith('/memories/m1');
  });
});

describe('exportSessionMemories', { tags: ['unit'] }, () => {
  it('calls GET /sessions/:id/memories/export with format param', async () => {
    const blob = new Blob(['test']);
    mockApi.get.mockResolvedValue({ data: blob });

    const result = await exportSessionMemories('s1', 'json');

    expect(mockApi.get).toHaveBeenCalledWith('/sessions/s1/memories/export', { params: { format: 'json' }, responseType: 'blob' });
    expect(result).toBe(blob);
  });

  it('passes md format', async () => {
    mockApi.get.mockResolvedValue({ data: new Blob() });

    await exportSessionMemories('s1', 'md');

    expect(mockApi.get).toHaveBeenCalledWith('/sessions/s1/memories/export', { params: { format: 'md' }, responseType: 'blob' });
  });
});

describe('getRun', { tags: ['unit'] }, () => {
  it('calls GET /runs/:id', async () => {
    mockApi.get.mockResolvedValue({ data: { id: 'r1', status: 'completed' } });

    const result = await getRun('r1');

    expect(mockApi.get).toHaveBeenCalledWith('/runs/r1');
    expect(result).toEqual({ id: 'r1', status: 'completed' });
  });
});

describe('listRuns', { tags: ['unit'] }, () => {
  it('calls GET /runs with default params', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    await listRuns();

    expect(mockApi.get).toHaveBeenCalledWith('/runs', { params: { limit: 20 } });
  });

  it('passes custom limit and offset', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    await listRuns(10, 5);

    expect(mockApi.get).toHaveBeenCalledWith('/runs', { params: { limit: 10, offset: 5 } });
  });
});

describe('healthCheck', { tags: ['unit'] }, () => {
  it('calls GET /health', async () => {
    mockApi.get.mockResolvedValue({ data: { status: 'ok' } });

    const result = await healthCheck();

    expect(mockApi.get).toHaveBeenCalledWith('/health');
    expect(result).toEqual({ status: 'ok' });
  });
});
