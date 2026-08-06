import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LazyCodeBlock from '@/components/AgentStudio/messages/LazyCodeBlock';

describe('LazyCodeBlock', { tags: ['unit'] }, () => {
  it('renders fallback code element while loading', () => {
    render(<LazyCodeBlock t={(k) => k}>test code</LazyCodeBlock>);
    expect(screen.getByText('test code')).toBeDefined();
  });
});
