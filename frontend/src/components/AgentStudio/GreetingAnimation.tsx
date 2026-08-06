import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

export default function GreetingAnimation({ onComplete }: { onComplete?: () => void }) {
  const { t } = useTranslation();
  const greeting = t('home.greeting');
  const reduceMotion =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [displayedText, setDisplayedText] = useState(() => (reduceMotion ? greeting : ''));
  const indexRef = useRef(0);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  });

  useEffect(() => {
    if (reduceMotion) {
      onCompleteRef.current?.();
      return;
    }

    indexRef.current = 0;

    const interval = setInterval(() => {
      indexRef.current++;
      setDisplayedText(greeting.slice(0, indexRef.current));
      if (indexRef.current >= greeting.length) {
        clearInterval(interval);
        onCompleteRef.current?.();
      }
    }, 100);

    return () => clearInterval(interval);
  }, [greeting, reduceMotion]);

  return (
    <h1 className="text-3xl leading-[1.2] font-bold tracking-tight text-[var(--color-text-primary)] m-0 mb-2 inline-flex items-center text-balance">
      {reduceMotion ? greeting : displayedText}
      {!reduceMotion && displayedText.length < greeting.length && (
        <span className="inline-block text-[var(--color-text-muted)] font-light animate-[blink_0.8s_step-end_infinite] ml-0.5">|</span>
      )}
    </h1>
  );
}
