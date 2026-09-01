import { useChatStore } from '../../../stores/chatStore';
import { setSessionCache } from '../../../stores/sessionCache';
import { TestProviders } from '../../../test/setup';
import RagBaseWorkstation from '../RagBaseWorkstation';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  params: vi.fn(() => ({ sessionId: undefined })),
  listSessions: vi.fn(),
  getSessionDetail: vi.fn(),
  deleteSession: vi.fn(),
  renameSession: vi.fn(),
  pinSession: vi.fn(),
  listModels: vi.fn(),
  submitRequirement: vi.fn(),
  retry: vi.fn(),
  navigate: vi.fn(),
  auth: {
    user: null,
    isAuthenticated: false,
    loading: false,
    loginModalOpen: false,
    loginModalView: 'login' as const,
    loginModalEmail: '',
    login: vi.fn(),
    register: vi.fn(),
    verify: vi.fn(),
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
    logout: vi.fn(),
    resendVerification: vi.fn(),
    sendRegisterCode: vi.fn(),
    openLoginModal: vi.fn(),
    closeLoginModal: vi.fn(),
    setLoginModalEmail: vi.fn(),
    refetchUser: vi.fn(),
  },
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mocks.navigate,
  useParams: () => mocks.params(),
}));

vi.mock('../../../api/client/sessions', () => ({
  listSessions: mocks.listSessions,
  getSessionDetail: mocks.getSessionDetail,
  deleteSession: mocks.deleteSession,
  renameSession: mocks.renameSession,
  pinSession: mocks.pinSession,
}));

vi.mock('../../../api/client/models', () => ({
  listModels: mocks.listModels,
}));

vi.mock('../../../stores/chatActions', () => ({
  submitRequirement: mocks.submitRequirement,
  retry: mocks.retry,
  continueGeneration: vi.fn(),
  editAndRegenerate: vi.fn(),
  regenerateMessage: vi.fn(),
}));

vi.mock('../../../components/auth/AuthContext', () => ({
  useAuth: () => mocks.auth,
}));

vi.mock('../../input/InputToolbar', () => ({
  default: () => <div data-testid="mock-input-toolbar" />,
}));

function renderWorkstation() {
  return render(
    <TestProviders>
      <RagBaseWorkstation />
    </TestProviders>,
  );
}

describe('RagBaseWorkstation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mocks.params.mockReturnValue({ sessionId: undefined });
    mocks.auth.isAuthenticated = false;
    mocks.listSessions.mockResolvedValue([]);
    mocks.listModels.mockResolvedValue([]);
    mocks.getSessionDetail.mockRejectedValue(new Error('n/a'));
    useChatStore.setState({
      status: 'idle',
      error: null,
      messages: [],
      interruptedMessageId: null,
      continuingId: null,
    });
    // 恢复 matchMedia 桌面默认（测试间不泄漏视口状态）
    (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(
      () => ({
        matches: false,
        media: '',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    );
  });

  it('renders HomeScreen when there are no messages', () => {
    renderWorkstation();
    expect(screen.getByText('home.subtitle')).toBeInTheDocument();
    expect(screen.getByTestId('mock-input-toolbar')).toBeInTheDocument();
  });

  it('renders messages panel when a conversation session is active', async () => {
    mocks.params.mockReturnValue({ sessionId: 's1' });
    setSessionCache('s1', {
      loaded: [
        {
          id: 'm1',
          role: 'user',
          agent_name: '',
          content: '存储里的消息',
          round_number: 1,
          created_at: '2026-01-01T00:00:00Z',
          userVersions: ['存储里的消息'],
          currentUserVersion: 0,
          answerVersions: ['a'],
          currentAnswerVersion: 0,
          attachments: [],
          thinkingDone: true,
        },
      ],
      active: 'r1',
    });
    renderWorkstation();
    expect(await screen.findByText('存储里的消息')).toBeInTheDocument();
    expect(screen.getByTestId('mock-input-toolbar')).toBeInTheDocument();
  });

  it('shows API error banner and retries on click', async () => {
    renderWorkstation();
    act(() => {
      useChatStore.setState({ status: 'error', error: '连不上后端' });
    });
    expect(screen.getByRole('alert')).toHaveTextContent('连不上后端');
    fireEvent.click(screen.getByText('common.retry'));
    expect(mocks.retry).toHaveBeenCalled();
  });

  it('toggles dark mode through settings', async () => {
    renderWorkstation();
    fireEvent.click(screen.getByRole('button', { name: 'Toggle dark mode' }));
    await waitFor(() => {
      const saved = JSON.parse(
        localStorage.getItem('ragbase-settings') ?? '{}',
      );
      expect(saved.theme).toBe('light');
    });
  });

  it('collapses the sidebar', () => {
    renderWorkstation();
    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
    // After collapse, the sidebar is hidden (width=0)
    const aside = document.querySelector('aside');
    expect(aside?.classList.contains('w-0')).toBe(true);
  });

  it('starts with the drawer closed on a mobile viewport', () => {
    // 移动视口（<768px）：useIsMobile → true，侧边栏应为收起抽屉态
    (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(
      (query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    );
    renderWorkstation();
    const aside = document.querySelector('aside');
    expect(aside?.classList.contains('fixed')).toBe(true);
    expect(aside?.classList.contains('-translate-x-full')).toBe(true);
    expect(aside?.classList.contains('w-0')).toBe(false);
  });

  it('forces the drawer closed when the viewport crosses to mobile', async () => {
    // 桌面打开页面（侧边栏展开）→ 窗口缩到手机宽度，
    // 侧边栏必须收起为抽屉态（此前以展开态压住消息区——占屏 70%+）。
    let currentMatches = false;
    const listeners = new Set<() => void>();
    (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(
      (query: string) => ({
        get matches() {
          return currentMatches;
        },
        media: query,
        onchange: null,
        addEventListener: vi.fn((_: string, cb: () => void) =>
          listeners.add(cb),
        ),
        removeEventListener: vi.fn((_: string, cb: () => void) =>
          listeners.delete(cb),
        ),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    );
    renderWorkstation();
    let aside = document.querySelector('aside');
    expect(aside?.classList.contains('fixed')).toBe(false);

    currentMatches = true;
    act(() => {
      listeners.forEach((cb) => cb());
    });

    await waitFor(() => {
      aside = document.querySelector('aside');
      expect(aside?.classList.contains('fixed')).toBe(true);
      expect(aside?.classList.contains('-translate-x-full')).toBe(true);
    });
  });

  it('renders conversations from the sessions query when authenticated', async () => {
    mocks.auth.isAuthenticated = true;
    mocks.listSessions.mockResolvedValue([
      {
        id: 's1',
        title: '历史会话A',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        run_count: 1,
        is_pinned: false,
      },
    ]);
    renderWorkstation();
    expect(await screen.findByText('历史会话A')).toBeInTheDocument();
  });

  it('starts a new chat via sidebar button', () => {
    renderWorkstation();
    fireEvent.click(screen.getByText('sidebar.newChat'));
    expect(mocks.navigate).toHaveBeenCalledWith('/');
  });
});
