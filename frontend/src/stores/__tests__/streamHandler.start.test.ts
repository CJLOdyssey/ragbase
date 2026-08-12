import { handleStreamStart } from '../streamHandler';
import { describe, expect, it, vi } from 'vitest';
import { makeMsg, makeState } from './helpers/streamHandlerTestUtils';

vi.mock('../utils/logger', () => ({
  default: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
}));

vi.mock('./uid', () => ({ uid: vi.fn(() => 'uid-fixed') }));

describe('handleStreamStart', { tags: ['unit'] }, () => {
  it('creates new message with chunk when no continuingId', () => {
    const s = makeState();
    const msg = { type: 'stream' as const, content: '', agent_name: 'Bot' };
    const result = handleStreamStart(s as never, msg, 'hello');

    expect(result.streamingId).toBeDefined();
    expect(result.messages![0].content).toBe('hello');
    expect(result.messages![0].agent_name).toBe('Bot');
    expect(result.currentRole).toBe('Bot');
  });

  it('defaults agent name to Agent', () => {
    const s = makeState();
    const result = handleStreamStart(s as never, { type: 'stream' }, 'hi');

    expect(result.messages![0].agent_name).toBe('Agent');
  });

  it('replaces continuing message when continuingId present', () => {
    const s = makeState({
      continuingId: 'msg-1',
      messages: [
        makeMsg('msg-1', { content: 'interrupted', thinking: 'was thinking' }),
      ],
    });

    const result = handleStreamStart(
      s as never,
      { type: 'stream', agent_name: 'Bot' },
      ' continues',
    );

    expect(result.continuingId).toBeNull();
    expect(result.messages![0].content).toBe('interrupted continues');
    expect(result.messages![0].agent_name).toBe('Agent');
  });

  it('clears pendingVersions during continuation (no archival in branch model)', () => {
    // Branch model (edit=新分支 run, ee48c1d): pendingVersions is a dead field —
    // the interrupted message is REPLACED by the continuation stream, never
    // archived into versions.
    const s = makeState({
      continuingId: 'msg-1',
      pendingVersions: ['v1'],
      pendingThinkingVersions: ['t1'],
      messages: [makeMsg('msg-1', { content: 'old', thinking: 'old-think' })],
    });

    const result = handleStreamStart(s as never, { type: 'stream' }, ' new');

    expect(result.pendingVersions).toBeNull();
    expect(result.messages![0].versions).toBeUndefined();
    expect(result.messages![0].content).toBe('old new');
  });

  it('clears pendingVersions for new stream (no continuingId)', () => {
    const s = makeState({
      pendingVersions: ['v0'],
      pendingThinkingVersions: ['t0'],
    });

    const result = handleStreamStart(s as never, { type: 'stream' }, 'first');

    expect(result.pendingVersions).toBeNull();
    expect(result.messages![0].versions).toBeUndefined();
    expect(result.messages![0].content).toBe('first');
  });

  it('merges edit-regenerate answer into the target message (keeps other messages)', () => {
    const s = makeState({
      editTargetId: 'a1',
      messages: [
        makeMsg('u1', { role: 'user', content: 'new question' }),
        makeMsg('a1', { content: 'old answer', thinking: 'old think' }),
        makeMsg('a2', { content: 'later message' }),
      ],
    });

    const result = handleStreamStart(
      s as never,
      { type: 'stream', agent_name: 'Bot' },
      ' fresh',
    );

    expect(result.editTargetId).toBeNull();
    // Edit = new branch run: the target message is remapped to the new run's
    // message and the stream starts FRESH — old answer is NOT archived as a
    // version (branch navigation replaces it, DB keeps it).
    expect(result.messages![1].versions).toBeUndefined();
    expect(result.messages![1].content).toBe(' fresh');
    expect(result.messages![1].thinking).toBe('');
    expect(result.messages![1].currentVersion).toBeUndefined();
    // Other messages preserved — nothing deleted.
    expect(result.messages!.map((m) => m.id)).toEqual([
      'u1',
      result.messages![1].id,
      'a2',
    ]);
  });
});
