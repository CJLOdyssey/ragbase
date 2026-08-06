import { useCallback, useRef, useState } from 'react';

export function useCopyToClipboard() {
  const copiedRef = useRef<Record<string, boolean>>({});
  const [, setTick] = useState(0);

  const copy = useCallback(async (text: string, key?: string) => {
    const id = key || '_default';
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      copiedRef.current[id] = true;
      setTick((n) => n + 1);
      setTimeout(() => {
        copiedRef.current[id] = false;
        setTick((n) => n + 1);
      }, 1000);
      return true;
    } catch {
      copiedRef.current[id] = false;
      setTick((n) => n + 1);
      return false;
    }
  }, []);

  const isCopied = useCallback((key?: string) => {
    return !!copiedRef.current[key || '_default'];
  }, []);

  return { copy, isCopied };
}
