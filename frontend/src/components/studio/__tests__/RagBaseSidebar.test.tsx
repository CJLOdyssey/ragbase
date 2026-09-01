import { TestProviders } from '../../../test/setup';
import type { Conversation } from '../../../types/studio';
import RagBaseSidebar from '../RagBaseSidebar';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { language: 'zh-CN' },
  }),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock('../sidebar/UserMenu', () => ({
  default: () => <div data-testid="mock-user-menu" />,
}));

const CONV: Conversation = {
  id: 'c1',
  title: '会话一',
  messages: [],
  createdAt: '',
  updatedAt: '',
  runCount: 1,
};

const baseProps = {
  conversations: [CONV],
  activeConvId: null,
  isUserMenuOpen: false,
  setIsUserMenuOpen: vi.fn(),
  setIsSettingsOpen: vi.fn(),
  setIsApiOpen: vi.fn(),
  setActiveConvId: vi.fn(),
  setInputValue: vi.fn(),
  onDeleteConversation: vi.fn(),
  onRenameConversation: vi.fn(),
  onPinConversation: vi.fn(),
  onNewChat: vi.fn(),
  isSidebarOpen: true,
  onToggleSidebar: vi.fn(),
  isMobile: false,
  onCloseSidebar: vi.fn(),
  activeView: 'chat' as const,
  onNavigate: vi.fn(),
};

function renderSidebar(extra: Record<string, unknown> = {}) {
  return render(
    <TestProviders>
      <RagBaseSidebar {...baseProps} {...extra} />
    </TestProviders>,
  );
}

describe('RagBaseSidebar', () => {
  it('renders brand, new chat button and conversation list', () => {
    renderSidebar();
    expect(screen.getByText('RagBase')).toBeInTheDocument();
    expect(screen.getByText('sidebar.newChat')).toBeInTheDocument();
    expect(screen.getByText('会话一')).toBeInTheDocument();
    expect(screen.getByTestId('mock-user-menu')).toBeInTheDocument();
  });

  it('triggers onNewChat', () => {
    const onNewChat = vi.fn();
    renderSidebar({ onNewChat });
    fireEvent.click(screen.getByText('sidebar.newChat'));
    expect(onNewChat).toHaveBeenCalled();
  });

  it('collapses via the toggle button', () => {
    const onToggleSidebar = vi.fn();
    renderSidebar({ onToggleSidebar });
    fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
    expect(onToggleSidebar).toHaveBeenCalled();
  });

  it('selecting a conversation activates it', () => {
    const setActiveConvId = vi.fn();
    const setInputValue = vi.fn();
    renderSidebar({ setActiveConvId, setInputValue });
    fireEvent.click(screen.getByText('会话一'));
    expect(setActiveConvId).toHaveBeenCalledWith('c1');
    expect(setInputValue).toHaveBeenCalledWith('会话一');
  });

  it('delegates delete to onDeleteConversation via context menu', () => {
    const onDeleteConversation = vi.fn();
    renderSidebar({ onDeleteConversation });
    fireEvent.click(screen.getByRole('button', { name: 'sidebar.more' }));
    fireEvent.click(screen.getByText('confirm.delete'));
    expect(onDeleteConversation).toHaveBeenCalledWith('c1');
  });

  it('mobile drawer: renders overlay when open and closes on overlay click', () => {
    const onCloseSidebar = vi.fn();
    renderSidebar({ isMobile: true, onCloseSidebar });
    // 移动端抽屉打开（isSidebarOpen=true）→ 遮罩存在
    fireEvent.click(screen.getByTestId('sidebar-overlay'));
    expect(onCloseSidebar).toHaveBeenCalled();
  });

  it('mobile drawer: header button closes instead of collapsing', () => {
    const onCloseSidebar = vi.fn();
    const onToggleSidebar = vi.fn();
    renderSidebar({ isMobile: true, onCloseSidebar, onToggleSidebar });
    fireEvent.click(screen.getByRole('button', { name: 'Close sidebar' }));
    expect(onCloseSidebar).toHaveBeenCalled();
    expect(onToggleSidebar).not.toHaveBeenCalled();
  });

  it('mobile drawer: closed state hides overlay and translates aside off-screen', () => {
    renderSidebar({
      isMobile: true,
      isSidebarOpen: false,
      onCloseSidebar: vi.fn(),
    });
    // 关闭态：遮罩不应渲染，aside 应 off-screen
    expect(screen.queryByTestId('sidebar-overlay')).toBeNull();
    const aside = document.querySelector('aside');
    expect(aside?.classList.contains('fixed')).toBe(true);
    expect(aside?.classList.contains('-translate-x-full')).toBe(true);
  });
});
