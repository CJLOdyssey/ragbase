/* eslint-disable @typescript-eslint/no-explicit-any */
import { vi } from 'vitest';

// react-syntax-highlighter
vi.mock('react-syntax-highlighter', () => ({
  default: ({ children }: any) => children,
  Prism: ({ children }: any) => <>{children}</>,
  Light: ({ children }: any) => <>{children}</>,
}));
vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({}));

// reactflow
vi.mock('reactflow', () => ({
  ReactFlow: ({ children }: any) => <>{children}</>,
  Handle: ({ children }: any) => <>{children}</>,
  Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
  addEdge: (e: any) => e,
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
}));

// @ant-design/icons
vi.mock('@ant-design/icons', () => {
  const MockIcon = () => null as any;
  return new Proxy({}, {
    get: () => MockIcon,
  });
});

// @ant-design/cssinjs
vi.mock('@ant-design/cssinjs', () => ({
  StyleProvider: ({ children }: any) => children,
  createCache: () => ({}),
}));
