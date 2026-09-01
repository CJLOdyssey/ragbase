import MobileModal from '@/components/shared/MobileModal';
import { TestProviders } from '@/test/setup';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

function mockViewport(isMobile: boolean) {
  (window.matchMedia as ReturnType<typeof vi.fn>).mockImplementation(() => ({
    matches: isMobile,
    media: '',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

/** antd lazyRender：container DOM 在动画触发后经 MutationObserver 绑定，
 *  派发手势前 flush microtask 等待绑定完成。 */
async function getSheetContainer() {
  await act(async () => {});
  const container = document.body.querySelector(
    '.mobile-sheet-wrap .ant-modal-container',
  ) as HTMLElement;
  expect(container).not.toBeNull();
  return container;
}

describe('MobileModal', { tags: ['unit'] }, () => {
  beforeEach(() => {
    mockViewport(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function renderModal(props: Partial<React.ComponentProps<typeof MobileModal>> = {}) {
    return render(
      <TestProviders>
        <MobileModal open title="Modal Title" onClose={vi.fn()} {...props}>
          content
        </MobileModal>
      </TestProviders>,
    );
  }

  function getDialog() {
    return document.body.querySelector('[role="dialog"]') as HTMLElement;
  }

  it('desktop: renders as plain dialog regardless of mode', () => {
    renderModal({ mode: 'fullscreen' });
    expect(getDialog().className).not.toContain('mobile-fullscreen');
    expect(getDialog().className).not.toContain('mobile-sheet');
  });

  it('mobile: fullscreen mode attaches mobile-fullscreen class', () => {
    mockViewport(true);
    renderModal({ mode: 'fullscreen' });
    expect(getDialog().className).toContain('mobile-fullscreen');
  });

  it('mobile: sheet mode attaches mobile-sheet classes and renders grip', () => {
    mockViewport(true);
    renderModal({ mode: 'sheet' });
    const dialog = getDialog();
    expect(dialog.className).toContain('mobile-sheet');
    expect(
      document.body.querySelector('.mobile-sheet-wrap .ant-modal-container'),
    ).not.toBeNull();
    // 抓柄（aria-hidden，不参与查询）
    expect(dialog.querySelector('.rounded-full')).not.toBeNull();
  });

  it('mobile: dialog mode stays plain', () => {
    mockViewport(true);
    renderModal({ mode: 'dialog' });
    expect(getDialog().className).not.toContain('mobile-fullscreen');
    expect(getDialog().className).not.toContain('mobile-sheet');
  });

  it('mobile: sheet drag past threshold closes after exit animation', async () => {
    vi.useFakeTimers();
    mockViewport(true);
    const onClose = vi.fn();
    renderModal({ mode: 'sheet', onClose });
    const container = await getSheetContainer();

    fireEvent.pointerDown(container, { clientY: 100 });
    fireEvent.pointerMove(window, { clientY: 240 });
    fireEvent.pointerUp(window);

    vi.advanceTimersByTime(180);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('mobile: sheet drag under threshold bounces back without closing', async () => {
    mockViewport(true);
    const onClose = vi.fn();
    renderModal({ mode: 'sheet', onClose });
    const container = await getSheetContainer();

    fireEvent.pointerDown(container, { clientY: 100 });
    fireEvent.pointerUp(window);

    expect(onClose).not.toHaveBeenCalled();
    expect(container.style.transform).toBe('translateY(0px)');
  });

  it('renders children content', () => {
    renderModal({ mode: 'fullscreen' });
    expect(screen.getByText('content')).toBeInTheDocument();
  });
});