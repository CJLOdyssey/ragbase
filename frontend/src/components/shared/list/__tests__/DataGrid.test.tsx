import { TestProviders } from '../../../../test/setup';
import DataGrid from '../DataGrid';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

interface Item {
  id: string;
  name: string;
}

const items: Item[] = [
  { id: 'a', name: 'one' },
  { id: 'b', name: 'two' },
];

describe('DataGrid', { tags: ['unit'] }, () => {
  it('renders every item via renderItem without wrapper DOM', () => {
    const { container } = render(
      <TestProviders>
        <DataGrid
          items={items}
          itemKey={(i) => i.id}
          renderItem={(i) => (
            <button type="button" data-testid={`card-${i.id}`}>
              {i.name}
            </button>
          )}
        />
      </TestProviders>,
    );
    expect(screen.getByTestId('card-a').textContent).toBe('one');
    expect(screen.getByTestId('card-b').textContent).toBe('two');
    // grid container is the only wrapper — cards are direct children
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.className).toContain('grid');
    expect(grid.children.length).toBe(2);
    expect(grid.children[0].tagName).toBe('BUTTON');
  });

  it('default minCardWidth is 300px', () => {
    const { container } = render(
      <TestProviders>
        <DataGrid
          items={items}
          itemKey={(i) => i.id}
          renderItem={(i) => <div>{i.name}</div>}
        />
      </TestProviders>,
    );
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.style.gridTemplateColumns).toContain('minmax(300px,1fr)');
  });

  it('custom minCardWidth applied', () => {
    const { container } = render(
      <TestProviders>
        <DataGrid
          items={items}
          itemKey={(i) => i.id}
          minCardWidth={240}
          renderItem={(i) => <div>{i.name}</div>}
        />
      </TestProviders>,
    );
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.style.gridTemplateColumns).toContain('minmax(240px,1fr)');
  });
});
