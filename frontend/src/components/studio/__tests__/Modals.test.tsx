import Modals from '../Modals';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../settings/SettingsModal', () => ({
  default: () => <div data-testid="settings-modal" />,
}));

vi.mock('../../settings/ApiManagementModal', () => ({
  default: () => <div data-testid="api-modal" />,
}));

describe('Modals', () => {
  it('renders nothing when both closed', () => {
    render(
      <Modals
        isSettingsOpen={false}
        isApiOpen={false}
        onCloseSettings={vi.fn()}
        onCloseApi={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('settings-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('api-modal')).not.toBeInTheDocument();
  });

  it('renders SettingsModal when open', () => {
    render(
      <Modals
        isSettingsOpen
        isApiOpen={false}
        onCloseSettings={vi.fn()}
        onCloseApi={vi.fn()}
      />,
    );
    expect(screen.getByTestId('settings-modal')).toBeInTheDocument();
  });

  it('renders ApiManagementModal when open', () => {
    render(
      <Modals
        isSettingsOpen={false}
        isApiOpen
        onCloseSettings={vi.fn()}
        onCloseApi={vi.fn()}
      />,
    );
    expect(screen.getByTestId('api-modal')).toBeInTheDocument();
  });
});
