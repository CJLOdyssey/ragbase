import { useDragAndDrop } from '../useDragAndDrop';
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

/* eslint-disable @typescript-eslint/no-explicit-any */

describe('useDragAndDrop', { tags: ['unit'] }, () => {
  const createMockRef = () => ({ current: { addFiles: vi.fn() } }) as any;

  it('starts with isPageDragOver false', () => {
    const { result } = renderHook(() => useDragAndDrop(createMockRef()));
    expect(result.current.isPageDragOver).toBe(false);
  });

  it('sets isPageDragOver true on drag over', () => {
    const { result } = renderHook(() => useDragAndDrop(createMockRef()));
    const e = { preventDefault: vi.fn() } as any;
    act(() => {
      result.current.handlePageDragOver(e);
    });
    expect(result.current.isPageDragOver).toBe(true);
  });

  it('sets isPageDragOver false on drag leave when same target', () => {
    const { result } = renderHook(() => useDragAndDrop(createMockRef()));
    act(() => {
      result.current.handlePageDragOver({ preventDefault: vi.fn() } as any);
    });
    expect(result.current.isPageDragOver).toBe(true);
    const target = document.createElement('div');
    const e = { currentTarget: target, target, relatedTarget: null } as any;
    act(() => {
      result.current.handlePageDragLeave(e);
    });
    expect(result.current.isPageDragOver).toBe(false);
  });

  it('calls addFiles on drop with files', () => {
    const ref = createMockRef();
    const { result } = renderHook(() => useDragAndDrop(ref));
    const file = new File(['test'], 'test.txt');
    const e = {
      preventDefault: vi.fn(),
      dataTransfer: { files: [file] },
    } as any;
    act(() => {
      result.current.handlePageDrop(e);
    });
    expect(ref.current.addFiles).toHaveBeenCalledWith([file]);
    expect(result.current.isPageDragOver).toBe(false);
  });
});
