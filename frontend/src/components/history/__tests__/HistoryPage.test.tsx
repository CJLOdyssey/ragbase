import { TestProviders } from '../../../test/setup';
import HistoryPage from '../HistoryPage';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mocks } = vi.hoisted(() => ({
  mocks: {
    listSessions: vi.fn(),
  },
}));

vi.mock('../../../api/client/sessions', () => ({
  listSessions: mocks.listSessions,
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
  it('shows empty state when no sessions', async () => {
    mocks.listSessions.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('暂无创作记录')).toBeTruthy();
  });

  it('renders session list', async () => {
    mocks.listSessions.mockResolvedValue([
      {
        id: 's1',
        title: 'AI 写作技巧',
        kind: 'normal',
        run_count: 2,
        created_at: '2026-08-01T10:00:00',
        updated_at: '2026-08-01T10:30:00',
      },
      {
        id: 's2',
        title: '小红书爆款标题',
        kind: 'normal',
        run_count: 1,
        created_at: '2026-08-02T09:00:00',
        updated_at: '2026-08-02T09:00:00',
      },
    ]);
    renderPage();
    expect(await screen.findByTestId('history-item-s1')).toBeTruthy();
    expect(screen.getByTestId('history-item-s2')).toBeTruthy();
    expect(screen.getByText('AI 写作技巧')).toBeTruthy();
    expect(screen.getByText('2 runs')).toBeTruthy();
  });

  it('shows loading text while fetching', () => {
    mocks.listSessions.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText('加载中…')).toBeTruthy();
  });
});
