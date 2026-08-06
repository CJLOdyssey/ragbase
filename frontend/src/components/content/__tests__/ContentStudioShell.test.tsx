import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ContentStudioShell from '../ContentStudioShell';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

describe('ContentStudioShell', { tags: ['unit'] }, () => {
  it('renders title and subtitle', () => {
    render(<ContentStudioShell />);
    expect(screen.getByText('app.title')).toBeDefined();
    expect(screen.getByText('app.subtitle')).toBeDefined();
  });
});
