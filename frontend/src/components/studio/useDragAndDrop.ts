import { useCallback, useState, type RefObject } from 'react';
import type * as React from 'react';
import type { InputToolbarHandle } from '../input/InputToolbar';

export function useDragAndDrop(inputToolbarRef: RefObject<InputToolbarHandle>) {
  const [isPageDragOver, setIsPageDragOver] = useState(false);

  const handlePageDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsPageDragOver(true);
  }, []);

  const handlePageDragLeave = useCallback((e: React.DragEvent) => {
    if (
      e.currentTarget === e.target ||
      !e.currentTarget.contains(e.relatedTarget as Node)
    ) {
      setIsPageDragOver(false);
    }
  }, []);

  const handlePageDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsPageDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        inputToolbarRef.current?.addFiles(Array.from(e.dataTransfer.files));
      }
    },
    [inputToolbarRef],
  );

  return {
    isPageDragOver,
    handlePageDragOver,
    handlePageDragLeave,
    handlePageDrop,
  };
}
