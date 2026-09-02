/**
 * Selected chat-persona prompt — localStorage single source of truth.
 * Mirrors the selected-model pattern: the selector UI writes here, the
 * submit path reads here; no React state crosses component trees.
 */
export const PROMPT_STORAGE_KEY = 'ragbase-selected-prompt';

export function readSelectedPromptId(): string | undefined {
  try {
    return localStorage.getItem(PROMPT_STORAGE_KEY) || undefined;
  } catch {
    return undefined;
  }
}

export function writeSelectedPromptId(id: string | null): void {
  try {
    if (id) localStorage.setItem(PROMPT_STORAGE_KEY, id);
    else localStorage.removeItem(PROMPT_STORAGE_KEY);
  } catch {
    // storage unavailable — selection applies for this session only
  }
}
