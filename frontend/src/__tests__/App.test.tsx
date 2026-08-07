import App from '../App';
import { TestProviders } from '../test/setup';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../components/studio/RagBaseWorkstation', () => ({
  default: () => <div data-testid="workstation">Workstation</div>,
}));

describe('App', { tags: ['unit'] }, () => {
  it('renders the workspace at root', async () => {
    render(
      <TestProviders>
        <App />
      </TestProviders>,
    );

    await vi.waitFor(
      () => {
        expect(screen.getByTestId('workstation')).toBeTruthy();
      },
      { timeout: 5000 },
    );
  });
});
