/// <reference types="vitest/config" />
import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import { defineConfig, loadEnv } from 'vite';
import type { Plugin } from 'vite';
import csp from 'vite-plugin-csp';
import { readFileSync } from 'fs';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const isDev = mode === 'development';
  // Shell env takes precedence over .env files, then defaults.
  // Ports per mode: hybrid 5174, full-container 5173, E2E 5175.
  const devPort =
    Number(process.env.VITE_DEV_PORT ?? env.VITE_DEV_PORT) || 5174;
  const apiOrigin =
    process.env.VITE_API_BASE_URL ||
    env.VITE_API_BASE_URL ||
    'http://localhost:8081';
  // Derive WS origin from API origin or use env override
  const wsOrigin =
    process.env.VITE_WS_URL ||
    env.VITE_WS_URL ||
    apiOrigin.replace(/^http/, 'ws');

  const appVersion = JSON.parse(
    readFileSync(path.resolve(__dirname, 'package.json'), 'utf-8'),
  ).version;

  return {
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    plugins: [
      tailwindcss(),
      react(),
      {
        name: 'sw-version-replace',
        apply: 'build',
        closeBundle() {
          const swPath = path.resolve(__dirname, 'dist/sw.js');
          try {
            const content = readFileSync(swPath, 'utf-8');
            const replaced = content.replace(/__APP_VERSION__/g, appVersion);
            require('fs').writeFileSync(swPath, replaced);
          } catch {}
        },
      } satisfies Plugin,
      csp({
        directives: {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'strict-dynamic'"],
          'style-src': ["'self'", "'unsafe-inline'"],
          'img-src': ["'self'", 'data:', 'https:'],
          'font-src': ["'self'", 'data:', 'https:'],
          'connect-src': [
            "'self'",
            apiOrigin,
            wsOrigin,
            ...(isDev ? ['http://localhost:*', 'ws://localhost:*'] : []),
          ],
          'frame-src': ["'none'"],
          'object-src': ["'none'"],
          'base-uri': ["'self'"],
          'form-action': ["'self'"],
        },
        hashStyle: 'sha256',
        enabled: env.VITE_ENABLE_STRICT_CSP === 'true',
      }),
      visualizer({ open: false, filename: 'dist/stats.html', gzipSize: true }),
    ],
    server: {
      port: devPort,
      proxy: {
        '/api': {
          target: apiOrigin,
          changeOrigin: true,
          ws: true,
        },
        '/ws': {
          target: wsOrigin,
          ws: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      minify: 'esbuild',
      cssMinify: true,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
            utils: ['axios', 'zustand'],
            sentry: ['@sentry/react', '@sentry/browser'],
            antd: ['antd', '@ant-design/icons', '@ant-design/cssinjs'],
            echarts: ['echarts'],
            motion: ['motion/react'],
          },
        },
      },
      chunkSizeWarningLimit: 500,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      pool: 'vmThreads',
      maxWorkers: 4,
      setupFiles: ['./src/test/global-mocks.tsx', './src/test/setup.tsx'],
      css: false,
      tags: [{ name: 'unit' }, { name: 'integration' }],
      deps: {
        optimizer: {
          ssr: {
            include: [
              'antd',
              '@ant-design/icons',
              'react-syntax-highlighter',
              'reactflow',
              '@ant-design/cssinjs',
              'echarts',
            ],
          },
        },
      },
      testTimeout: 15000,
      hookTimeout: 15000,
      exclude: ['e2e/**', 'node_modules/**'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov', 'html'],
        reportsDirectory: './coverage',
        clean: true,
        cleanOnRerun: false,
        processingConcurrency: 1,
        thresholds: {
          statements: 80,
          branches: 80,
          functions: 80,
          lines: 80,
        },
        include: ['src/**/*.{ts,tsx}'],
        exclude: [
          'src/**/__tests__/**',
          'src/test/**',
          'src/types/**',
          'src/main.tsx',
          'src/App.tsx',
          'src/**/index.ts',
          'src/api/websocket.ts',
          'src/api/hooks.ts',
          'src/api/client/instance.ts',
          'src/utils/logger.ts',
          'src/vite-env.d.ts',
        ],
      },
    },
  };
});
