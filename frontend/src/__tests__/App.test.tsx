import App from '../App';
import { TestProviders } from '../test/setup';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../components/content/ContentStudioShell', () => ({
  default: () => <div data-testid="content-studio-shell">ContentStudio</div>,
}));

vi.mock('../components/content/ComposerPage', () => ({
  default: () => <div data-testid="composer-page">Composer</div>,
}));

describe('App', { tags: ['unit'] }, () => {
  it('redirects root to /compose and renders ComposerPage', async () => {
    render(
      <TestProviders>
        <App />
      </TestProviders>,
    );

    await vi.waitFor(
      () => {
        expect(screen.getByTestId('composer-page')).toBeTruthy();
      },
      { timeout: 5000 },
    );
  });
});
