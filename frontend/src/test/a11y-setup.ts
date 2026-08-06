import { axe } from 'vitest-axe';
import { expect } from 'vitest';
import type { Result, RunOptions } from 'axe-core';

export async function expectNoA11yViolations(
  container: HTMLElement,
  options?: RunOptions,
): Promise<Result[]> {
  const results = await axe(container, options);
  expect(results.violations).toHaveLength(0);
  return results.violations;
}
