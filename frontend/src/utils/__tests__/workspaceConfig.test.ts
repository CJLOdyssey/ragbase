import { describe, it, expect } from 'vitest';
import { getAgentType, getWorkspaceTabs } from '../workspaceConfig';

describe('getAgentType', { tags: ['unit'] }, () => {
  it('returns ui for ui agent id', () => {
    expect(getAgentType('ui')).toBe('ui');
  });

  it('returns frontend for frontend agent id', () => {
    expect(getAgentType('frontend')).toBe('frontend');
  });

  it('returns backend for backend agent id', () => {
    expect(getAgentType('backend')).toBe('backend');
  });

  it('defaults to frontend for unknown agent id', () => {
    expect(getAgentType('unknown')).toBe('frontend');
  });
});

describe('getWorkspaceTabs', { tags: ['unit'] }, () => {
  it('returns ui tabs for ui type', () => {
    const tabs = getWorkspaceTabs('ui');
    expect(tabs).toHaveLength(2);
    expect(tabs[0].id).toBe('ui-code');
    expect(tabs[1].id).toBe('ui-preview');
  });

  it('returns frontend tabs for frontend type', () => {
    const tabs = getWorkspaceTabs('frontend');
    expect(tabs).toHaveLength(3);
    expect(tabs[0].id).toBe('frontend-code');
    expect(tabs[1].id).toBe('frontend-test');
    expect(tabs[2].id).toBe('frontend-preview');
  });

  it('returns backend tabs for backend type', () => {
    const tabs = getWorkspaceTabs('backend');
    expect(tabs).toHaveLength(2);
    expect(tabs[0].id).toBe('backend-code');
    expect(tabs[1].id).toBe('backend-test');
  });

  it('returns default tabs for invalid type', () => {
    const tabs = getWorkspaceTabs('invalid' as unknown as 'frontend');
    expect(tabs).toHaveLength(2);
    expect(tabs[0].id).toBe('code');
    expect(tabs[1].id).toBe('preview');
  });
});
