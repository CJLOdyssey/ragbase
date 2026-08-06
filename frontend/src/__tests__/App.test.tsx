import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';
import { TestProviders } from '../test/setup';

vi.mock('../components/content/ContentStudioShell', () => ({
  default: () => <div data-testid="content-studio-shell">ContentStudio</div>,
}));

describe('App', { tags: ['unit'] }, () => {
  it('renders without crashing', async () => {
    render(
      <TestProviders>
        <App />
      </TestProviders>,
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId('content-studio-shell')).toBeTruthy();
    }, { timeout: 5000 });
  });
});
