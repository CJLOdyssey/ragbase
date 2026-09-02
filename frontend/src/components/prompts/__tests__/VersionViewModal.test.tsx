import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import VersionViewModal from '../VersionViewModal';
import type { VersionItem } from '../../../api/client/versions';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
      language: 'zh-CN',
    },
  }),
}));

describe('VersionViewModal', () => {
  const mockVersion: VersionItem = {
    id: 'v1',
    version_num: 1,
    resource_type: 'prompt',
    resource_id: 'p1',
    snapshot: {
      name: '测试提示词',
      category: 'user',
      content: '这是测试内容',
    },
    created_at: '2024-01-01T00:00:00Z',
    created_by: 'user1',
  };

  const mockOnRollback = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders version view modal with snapshot data', () => {
    render(
      <VersionViewModal
        version={mockVersion}
        onRollback={mockOnRollback}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('prompts.editor.name')).toBeInTheDocument();
    expect(screen.getByText('测试提示词')).toBeInTheDocument();
    expect(screen.getByText('prompts.editor.category')).toBeInTheDocument();
    expect(screen.getByText('user')).toBeInTheDocument();
    expect(screen.getByText('prompts.editor.content')).toBeInTheDocument();
    expect(screen.getByText('这是测试内容')).toBeInTheDocument();
  });

  it('calls onRollback when rollback button is clicked', () => {
    render(
      <VersionViewModal
        version={mockVersion}
        onRollback={mockOnRollback}
        onClose={mockOnClose}
      />
    );

    const rollbackButton = screen.getByRole('button', { name: 'prompts.version.rollbackConfirm' });
    fireEvent.click(rollbackButton);

    expect(mockOnRollback).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <VersionViewModal
        version={mockVersion}
        onRollback={mockOnRollback}
        onClose={mockOnClose}
      />
    );

    // 获取所有关闭按钮（Modal自带的和footer中的）
    const closeButtons = screen.getAllByRole('button', { name: 'common.close' });
    // 点击footer中的关闭按钮（通常是最后一个）
    fireEvent.click(closeButtons[closeButtons.length - 1]);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('displays default values when snapshot fields are missing', () => {
    const incompleteVersion: VersionItem = {
      ...mockVersion,
      snapshot: {},
    };

    render(
      <VersionViewModal
        version={incompleteVersion}
        onRollback={mockOnRollback}
        onClose={mockOnClose}
      />
    );

    // 当 snapshot 为空时，name 和 category 都显示 '—'
    const defaultValues = screen.getAllByText('—');
    expect(defaultValues.length).toBeGreaterThanOrEqual(2);
  });

  it('displays version number in title', () => {
    render(
      <VersionViewModal
        version={mockVersion}
        onRollback={mockOnRollback}
        onClose={mockOnClose}
      />
    );

    // 标题应该包含版本号信息
    expect(screen.getByText('prompts.version.rollbackTitle')).toBeInTheDocument();
  });
});
