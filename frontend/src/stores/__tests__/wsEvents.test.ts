import { describe, it, expect } from 'vitest';
import type {
  WsStreamEvent,
  WsThinkingStreamEvent,
  WsMessageEvent,
  WsThinkingDoneEvent,
  WsInfoEvent,
  WsErrorEvent,
  WsBalanceWarningEvent,
  WsOpenUrlEvent,
  WsResultEvent,
  WsTeamResultEvent,
  WsThumbsEvent,
  WsEvent,
} from '../wsEvents';

describe('wsEvents types', { tags: ['unit'] }, () => {
  it('creates a WsStreamEvent', () => {
    const event: WsStreamEvent = { type: 'stream', content: 'hello', thinking: 'thinking', agent_name: 'agent1' };
    expect(event.type).toBe('stream');
    expect(event.content).toBe('hello');
    expect(event.thinking).toBe('thinking');
    expect(event.agent_name).toBe('agent1');
  });

  it('creates a WsThinkingStreamEvent', () => {
    const event: WsThinkingStreamEvent = { type: 'thinking_stream', content: 'thinking...', agent_name: 'agent2' };
    expect(event.type).toBe('thinking_stream');
    expect(event.content).toBe('thinking...');
  });

  it('creates a WsMessageEvent with round_number', () => {
    const event: WsMessageEvent = { type: 'message', content: 'msg', role: 'assistant', round_number: 2, agent_name: 'a1' };
    expect(event.type).toBe('message');
    expect(event.round_number).toBe(2);
    expect(event.role).toBe('assistant');
  });

  it('creates a WsThinkingDoneEvent', () => {
    const event: WsThinkingDoneEvent = { type: 'thinking_done', thinking: 'done thinking', agent_name: 'a1' };
    expect(event.type).toBe('thinking_done');
    expect(event.thinking).toBe('done thinking');
  });

  it('creates a WsInfoEvent', () => {
    const event: WsInfoEvent = { type: 'info', content: 'info msg', data: 'some data' };
    expect(event.type).toBe('info');
    expect(event.data).toBe('some data');
  });

  it('creates a WsErrorEvent', () => {
    const event: WsErrorEvent = { type: 'error', content: 'something went wrong' };
    expect(event.type).toBe('error');
  });

  it('creates a WsBalanceWarningEvent', () => {
    const event: WsBalanceWarningEvent = { type: 'balance_warning', content: 'low balance' };
    expect(event.type).toBe('balance_warning');
  });

  it('creates a WsOpenUrlEvent', () => {
    const event: WsOpenUrlEvent = { type: 'open_url', url: 'https://example.com' };
    expect(event.url).toBe('https://example.com');
  });

  it('creates a WsResultEvent with dynamic keys', () => {
    const event: WsResultEvent = { type: 'result', run_id: 'r1', status: 'done' };
    expect(event.type).toBe('result');
    expect(event.run_id).toBe('r1');
    expect(event.status).toBe('done');
  });

  it('creates a WsTeamResultEvent with dynamic keys', () => {
    const event: WsTeamResultEvent = { type: 'team_result', team_id: 't1' };
    expect(event.type).toBe('team_result');
    expect(event.team_id).toBe('t1');
  });

  it('creates a WsThumbsEvent', () => {
    const event: WsThumbsEvent = { type: 'thumbs', rating: 5 };
    expect(event.type).toBe('thumbs');
    expect(event.rating).toBe(5);
  });

  it('assigns WsEvent union type correctly', () => {
    const events: WsEvent[] = [
      { type: 'stream' },
      { type: 'thinking_stream' },
      { type: 'message' },
      { type: 'thinking_done' },
      { type: 'info' },
      { type: 'error' },
      { type: 'balance_warning' },
      { type: 'open_url' },
      { type: 'result' },
      { type: 'team_result' },
      { type: 'thumbs' },
    ];
    expect(events).toHaveLength(11);
  });
});
