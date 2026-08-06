import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('API Client', { tags: ['unit'] }, () => {
  describe('submitRequirement', () => {
    it('POST /api/runs 提交需求', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { run_id: 'run-1', status: 'running' },
      });
      const { submitRequirement } = await import('../client');
      const result = await submitRequirement('测试需求');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/runs', {
        requirement: '测试需求',
        session_id: undefined,
      });
      expect(result).toEqual({ run_id: 'run-1', status: 'running' });
    });

    it('传递 session_id 参数', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { run_id: 'run-1', status: 'running' },
      });
      const { submitRequirement } = await import('../client');
      await submitRequirement('需求', 'session-1');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/runs', {
        requirement: '需求',
        session_id: 'session-1',
      });
    });

    it('网络错误时抛出异常', async () => {
      mockAxiosInstance.post.mockRejectedValue(new Error('Network Error'));
      const { submitRequirement } = await import('../client');
      await expect(submitRequirement('需求')).rejects.toThrow();
    });
  });

  describe('Session API', () => {
    it('listSessions GET /api/sessions', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: [{ id: '1', title: '会话1' }],
      });
      const { listSessions } = await import('../client');
      const result = await listSessions(10);
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/sessions', {
        params: { limit: 10 },
      });
      expect(result).toEqual([{ id: '1', title: '会话1' }]);
    });

    it('getSessionDetail GET /api/sessions/:id', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: '1', title: '会话1', runs: [], memories: [] },
      });
      const { getSessionDetail } = await import('../client');
      const result = await getSessionDetail('1');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/sessions/1');
      expect(result.title).toBe('会话1');
    });

    it('createSession POST /api/sessions', async () => {
      mockAxiosInstance.post.mockResolvedValue({
        data: { id: 'new-id', title: '新对话' },
      });
      const { createSession } = await import('../client');
      const result = await createSession('新对话');
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/sessions', {
        title: '新对话',
      });
      expect(result).toEqual({ id: 'new-id', title: '新对话' });
    });

    it('renameSession PUT /api/sessions/:id', async () => {
      mockAxiosInstance.put.mockResolvedValue({});
      const { renameSession } = await import('../client');
      await renameSession('1', '新标题');
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/sessions/1', {
        title: '新标题',
      });
    });

    it('deleteSession DELETE /api/sessions/:id', async () => {
      mockAxiosInstance.delete.mockResolvedValue({});
      const { deleteSession } = await import('../client');
      await deleteSession('1');
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/sessions/1');
    });
  });

  describe('Memory API', () => {
    it('deleteMemory DELETE /api/memories/:id', async () => {
      mockAxiosInstance.delete.mockResolvedValue({});
      const { deleteMemory } = await import('../client');
      await deleteMemory('mem-1');
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/memories/mem-1');
    });

    it('exportSessionMemories GET 返回 Blob', async () => {
      const blob = new Blob(['data'], { type: 'application/json' });
      mockAxiosInstance.get.mockResolvedValue({ data: blob });
      const { exportSessionMemories } = await import('../client');
      const result = await exportSessionMemories('1', 'json');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/sessions/1/memories/export',
        {
          params: { format: 'json' },
          responseType: 'blob',
        },
      );
      expect(result).toBeInstanceOf(Blob);
    });
  });

  describe('Run API', () => {
    it('getRun GET /api/runs/:id', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: 'run-1', requirement: '需求' },
      });
      const { getRun } = await import('../client');
      const result = await getRun('run-1');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/runs/run-1');
      expect(result.requirement).toBe('需求');
    });

    it('listRuns GET /api/runs', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: [{ id: '1' }] });
      const { listRuns } = await import('../client');
      await listRuns(20);
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/runs', {
        params: { limit: 20 },
      });
    });
  });

  describe('Health API', () => {
    it('healthCheck GET /api/health', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { status: 'ok' } });
      const { healthCheck } = await import('../client');
      const result = await healthCheck();
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health');
      expect(result).toEqual({ status: 'ok' });
    });
  });
});
