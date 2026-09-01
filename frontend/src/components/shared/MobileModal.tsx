import { useEffect, useRef, type CSSProperties, type ReactNode } from 'react';
import { Modal as AntdModal } from 'antd';
import { useIsMobile } from '../../hooks/useMediaQuery';

/**
 * MobileModal — 移动端弹窗抽象（桌面端完全回退 antd Modal 默认行为）。
 *
 * 三层分级（<768px 视口生效，桌面端一律按 dialog 渲染）：
 *   dialog     — L1 轻确认，保持 antd 居中弹窗（不注入任何样式）
 *   sheet      — L2 中量任务，底部圆角 Sheet（antd wrapper 注入
 *                .mobile-sheet-wrap 贴底；支持下滑关闭手势与 44px 抓柄）
 *   fullscreen — L3 重量任务，全屏 + 三段式（header 收缩 / body 滚动 /
 *                footer 吸底），样式由 responsive.css 的 .mobile-fullscreen 提供
 *
 * 键盘：全屏/Sheet 内输入框聚焦时监听 visualViewport resize，
 * 自动滚动到可见区域（iOS Safari 键盘遮挡问题）。
 *
 * 手势绑定时机：antd Modal 的 lazyRender 使内容 DOM 在动画触发后才挂载
 * （effect 阶段尚不存在），用 MutationObserver 等待就绪后绑定，避免
 * 轮询 / afterOpenChange（jsdom 不回调）等不稳定方案。
 */

type MobileModalMode = 'dialog' | 'sheet' | 'fullscreen';

interface MobileModalProps {
  open: boolean;
  onClose: () => void;
  mode?: MobileModalMode;
  title?: ReactNode;
  width?: number;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

const CLOSE_DURATION_MS = 180;
const DRAG_RATIO = 0.3;
const FLING_VELOCITY_PX_MS = 0.5;

interface GestureState {
  startY: number;
  lastY: number;
  lastTime: number;
  offset: number;
  velocity: number;
  height: number;
}

/** 全屏/Sheet 三段式布局：container 纵向分配，body 弹性填充（CSS 兜底，
 *  业务弹窗可自行用 classNames.container / styles 覆盖细化）。 */
const mobileLayoutStyles: Record<'container' | 'body', CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  body: { flex: 1, minHeight: 0 },
};

/**
 * Sheet 下滑关闭手势。
 * 绑定在 antd 注入的 .mobile-sheet-wrap 内的 container 上（类名由
 * MobileModal 的 classNames.wrapper 保证，不依赖 antd 内部 DOM 结构）。
 * 内容滚动容器未回到顶部时手势让位于滚动（scrollTop > 0 不启动拖拽）。
 */
function useSheetDismiss(enabled: boolean, onClose: () => void) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const gestureRef = useRef<GestureState | null>(null);
  const closingRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    const findContainer = () =>
      document.querySelector<HTMLElement>(
        '.mobile-sheet-wrap .ant-modal-container',
      );

    // 每次打开重置手势状态（React 18 StrictMode 下 effect 双执行，幂等）
    closingRef.current = false;

    let cleanupListeners: (() => void) | undefined;

    const bind = (container: HTMLElement) => {
      container.style.transition = 'none';
      container.style.transform = '';

      const findScrollParent = (el: Element | null): HTMLElement | null => {
        const parent = el?.parentElement ?? null;
        if (!parent) return null;
        if (parent.scrollHeight > parent.clientHeight) return parent;
        return findScrollParent(parent);
      };

      const applyTransform = (dy: number, animate: boolean) => {
        container.style.transition = animate
          ? `transform ${CLOSE_DURATION_MS}ms var(--ease-out-quint)`
          : 'none';
        container.style.transform = `translateY(${dy}px)`;
      };

      const onPointerDown = (e: PointerEvent) => {
        if (closingRef.current) return;
        const scroller = findScrollParent(e.target as Element);
        if (scroller && scroller !== container && scroller.scrollTop > 0) return;
        gestureRef.current = {
          startY: e.clientY,
          lastY: e.clientY,
          lastTime: performance.now(),
          offset: 0,
          velocity: 0,
          height: container.offsetHeight,
        };
      };

      const onPointerMove = (e: PointerEvent) => {
        const g = gestureRef.current;
        if (!g) return;
        const now = performance.now();
        const dt = Math.max(1, now - g.lastTime);
        g.velocity = (e.clientY - g.lastY) / dt;
        g.lastY = e.clientY;
        g.lastTime = now;
        g.offset = Math.max(0, e.clientY - g.startY);
        applyTransform(g.offset, false);
      };

      const onPointerUp = () => {
        const g = gestureRef.current;
        gestureRef.current = null;
        if (!g) return;
        const overThreshold =
          g.offset > g.height * DRAG_RATIO || g.velocity > FLING_VELOCITY_PX_MS;
        if (overThreshold) {
          closingRef.current = true;
          applyTransform(g.height, true);
          window.setTimeout(() => onCloseRef.current(), CLOSE_DURATION_MS);
        } else {
          applyTransform(0, true);
        }
      };

      container.addEventListener('pointerdown', onPointerDown);
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
      cleanupListeners = () => {
        container.removeEventListener('pointerdown', onPointerDown);
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onPointerUp);
      };
    };

    const container = findContainer();
    if (container) {
      bind(container);
      return cleanupListeners;
    }

    // lazyRender：内容 DOM 延迟挂载，观察 body 子树直到 container 出现
    const observer = new MutationObserver(() => {
      const el = findContainer();
      if (el) {
        observer.disconnect();
        bind(el);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      cleanupListeners?.();
    };
  }, [enabled]);
}

/** Sheet 顶部抓柄：视觉提示可拖拽（iOS 惯例），不参与交互 */
function SheetGrip() {
  return (
    <div className="shrink-0 flex justify-center pt-2 pb-1" aria-hidden="true">
      <div className="w-9 h-1 rounded-full bg-[var(--color-border-strong)]" />
    </div>
  );
}

export default function MobileModal({
  open,
  onClose,
  mode = 'dialog',
  title,
  width,
  footer,
  children,
  className,
}: MobileModalProps) {
  const isMobile = useIsMobile();
  const isSheet = isMobile && mode === 'sheet';
  const isFullscreen = isMobile && mode === 'fullscreen';

  useSheetDismiss(isSheet && open, onClose);

  // 键盘：全屏/Sheet 输入框聚焦时，visualViewport 变化后滚动到可见区
  useEffect(() => {
    if (!(isFullscreen || isSheet) || !open) return;
    const viewport = window.visualViewport;
    if (!viewport) return;
    const onResize = () => {
      const el = document.activeElement;
      if (el instanceof HTMLElement && el.matches('input, textarea')) {
        el.scrollIntoView({ block: 'nearest' });
      }
    };
    viewport.addEventListener('resize', onResize);
    return () => viewport.removeEventListener('resize', onResize);
  }, [isFullscreen, isSheet, open]);

  const modalClassName = [
    isFullscreen ? 'mobile-fullscreen' : '',
    isSheet ? 'mobile-sheet' : '',
    className ?? '',
  ]
    .join(' ')
    .trim();

  return (
    <AntdModal
      open={open}
      onCancel={onClose}
      centered
      width={width}
      title={title}
      footer={footer}
      className={modalClassName || undefined}
      classNames={{ wrapper: isSheet ? 'mobile-sheet-wrap' : undefined }}
      styles={isFullscreen || isSheet ? mobileLayoutStyles : undefined}
    >
      {isSheet && <SheetGrip />}
      {children}
    </AntdModal>
  );
}