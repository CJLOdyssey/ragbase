import { lazy, Suspense } from 'react';
import type { ReactNode } from 'react';

const Inner = lazy(() => import('./CodeBlock').then((m) => ({ default: m.CodeBlock })));

interface Props {
  className?: string;
  children: ReactNode;
  t: (key: string) => string;
}

export default function LazyCodeBlock(props: Props) {
  return (
    <Suspense fallback={<code>{props.children}</code>}>
      <Inner {...props} />
    </Suspense>
  );
}
