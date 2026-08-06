import { TestProviders } from '../../../test/setup';
import HistoryPage from '../HistoryPage';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks } = vi.hoisted(() => ({
  mocks: {
    listGenerations: vi.fn(),
  },
}));

vi.mock('../../../api/client/generations', () => ({
  listGenerations: mocks.listGenerations,
}));

function renderPage() {
  return render(
    <TestProviders>
      <HistoryPage />
    </TestProviders>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('HistoryPage', { tags: ['unit'] }, () => {
  it('shows empty state when no generations', async () => {
    mocks.listGenerations.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('暂无创作记录')).toBeTruthy();
  });

  it('renders generation list with topic and type label', async () => {
    mocks.listGenerations.mockResolvedValue([
      {
        run_id: 'r1',
        session_id: null,
        topic: '小红书爆款标题',
        content_type: 'xiaohongshu',
        generation_mode: null,
        status: null,
        result: {},
        created_at: '2026-08-01T10:00:00',
      },
      {
        run_id: 'r2',
        session_id: 's2',
        topic: '公众号深度文',
        content_type: 'unknown_type',
        generation_mode: null,
        status: null,
        result: {},
        created_at: '2026-08-02T09:00:00',
      },
    ]);
    renderPage();
    expect(await screen.findByText('小红书爆款标题')).toBeTruthy();
    expect(screen.getByText('公众号深度文')).toBeTruthy();
    expect(screen.getByText('小红书笔记')).toBeTruthy();
    expect(screen.getByText('通用文案')).toBeTruthy();
  });

  it('disables view action', async () => {
    mocks.listGenerations.mockResolvedValue([
      {
        run_id: 'r1',
        session_id: null,
        topic: '营销文案初稿',
        content_type: 'marketing',
        generation_mode: null,
        status: null,
        result: {},
        created_at: null,
      },
    ]);
    renderPage();
    expect(await screen.findByRole('button', { name: '查看' })).toBeDisabled();
  });

  it('shows loading text while fetching', () => {
    mocks.listGenerations.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText('加载中…')).toBeTruthy();
  });
});
