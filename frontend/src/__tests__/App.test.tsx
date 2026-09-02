import App from '../App';
import { SettingsProvider } from '../contexts/SettingsContext';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../components/studio/RagBaseWorkstation', () => ({
  default: () => <div data-testid="workstation">Workstation</div>,
}));

describe('App', { tags: ['unit'] }, () => {
  it('renders the workspace at root', async () => {
    // App 自带 BrowserRouter/QueryClient/Toast/Auth，外部仅需 SettingsProvider
    // （与 main.tsx 一致）；TestProviders 的 MemoryRouter 会造成 Router 嵌套。
    render(
      <SettingsProvider>
        <App />
      </SettingsProvider>,
    );

    await vi.waitFor(
      () => {
        expect(screen.getByTestId('workstation')).toBeTruthy();
      },
      { timeout: 5000 },
    );
  });
});
