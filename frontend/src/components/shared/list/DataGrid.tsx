/**
 * DataGrid — responsive card grid shell.
 *
 * Visual baseline: auto-fill minmax cards with 14px gap (PromptGrid/AssetsGrid).
 * OCP: card content is fully delegated via renderItem.
 * Fragment keys keep the DOM free of extra wrappers so feature tests can
 * assert on card structure directly.
 */
import { Fragment } from 'react';
import type { ReactNode } from 'react';

interface DataGridProps<T> {
  items: T[];
  itemKey: (item: T) => string;
  renderItem: (item: T) => ReactNode;
  /** Minimum card width in px before wrapping. Default 300. */
  minCardWidth?: number;
}

export default function DataGrid<T>({
  items,
  itemKey,
  renderItem,
  minCardWidth = 300,
}: DataGridProps<T>) {
  return (
    <div
      className="grid gap-3.5"
      style={{
        gridTemplateColumns: `repeat(auto-fill,minmax(${minCardWidth}px,1fr))`,
      }}
    >
      {items.map((item) => (
        <Fragment key={itemKey(item)}>{renderItem(item)}</Fragment>
      ))}
    </div>
  );
}
