import ActionSheet from '@/components/shared/ActionSheet';
import { TestProviders } from '@/test/setup';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = { 'common.cancel': '取消' };
      return map[key] || key;
    },
  }),
}));

describe('ActionSheet', { tags: ['unit'] }, () => {
  function makeItems() {
    return [
      { key: 'rename', label: '重命名', onClick: vi.fn() },
      { key: 'delete', label: '删除', danger: true, onClick: vi.fn() },
    ];
  }

  function renderSheet(props: Partial<React.ComponentProps<typeof ActionSheet>> = {}) {
    return render(
      <TestProviders>
        <ActionSheet open items={makeItems()} onClose={vi.fn()} {...props} />
      </TestProviders>,
    );
  }

  it('renders all items plus cancel button', () => {
    renderSheet();
    expect(screen.getByText('重命名')).toBeInTheDocument();
    expect(screen.getByText('删除')).toBeInTheDocument();
    expect(screen.getByText('取消')).toBeInTheDocument();
  });

  it('clicking an item invokes its handler and closes', () => {
    const items = makeItems();
    const onClose = vi.fn();
    render(
      <TestProviders>
        <ActionSheet open items={items} onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('重命名'));
    expect(items[0].onClick).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('clicking cancel closes without invoking any item', () => {
    const items = makeItems();
    const onClose = vi.fn();
    render(
      <TestProviders>
        <ActionSheet open items={items} onClose={onClose} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('取消'));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(items[0].onClick).not.toHaveBeenCalled();
    expect(items[1].onClick).not.toHaveBeenCalled();
  });

  it('renders optional title', () => {
    renderSheet({ title: '操作' });
    expect(screen.getByText('操作')).toBeInTheDocument();
  });
});