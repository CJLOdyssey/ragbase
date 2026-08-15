import { disconnectRun } from '../api/websocket';
import type { ChatState } from './chatTypes';
import {
  handleBalanceWarningEvent,
  handleErrorEvent,
  handleInfoEvent,
  handleMessageEvent,
  handleOpenUrlEvent,
} from './messageHandler';
import {
  handleResultEvent,
  handleTeamResultEvent,
  handleThinkingDoneEvent,
  handleThumbsEvent,
} from './resultHandler';
import {
  handleApprovalRequest,
  handleStreamEvent,
  handleTeamResultMeta,
  handleThinkingStreamEvent,
} from './streamHandler';
import type { WsEvent } from './wsEvents';

type SetFn = (fn: (state: ChatState) => Partial<ChatState>) => void;
type GetFn = () => ChatState;

const _activeStreamMsgIds = new Set<string>();

export function createStreamHandler(set: SetFn, get: GetFn) {
  return (data: unknown) => {
    const msg = data as WsEvent;

    if (msg.type === 'stream') {
      handleStreamEvent(set, get, _activeStreamMsgIds, msg);
      return;
    }

    if (msg.type === 'thinking_stream') {
      handleThinkingStreamEvent(set, get, _activeStreamMsgIds, msg);
      return;
    }

    if (msg.type === 'message') {
      handleMessageEvent(set, msg);
      return;
    }

    if (msg.type === 'thinking_done') {
      handleThinkingDoneEvent(set, msg);
      return;
    }

    if (msg.type === 'info') {
      handleInfoEvent(set, msg);
      return;
    }

    if (msg.type === 'error') {
      handleErrorEvent(set, msg);
      // 后端 error 事件后 run 已终态：主动断开 WS。subscribe_run 只在
      // result 时关闭流，否则挂到 60s idle——每次 error 占 pubsub 一分钟，
      // 与 Redis 泄漏治理目标相悖。
      disconnectRun(get().currentRunId || '');
      return;
    }

    if (msg.type === 'balance_warning') {
      handleBalanceWarningEvent(set, msg);
      disconnectRun(get().currentRunId || '');
      return;
    }

    if (msg.type === 'open_url') {
      handleOpenUrlEvent(msg);
      return;
    }

    if (msg.type === 'result') {
      handleResultEvent(set, get, _activeStreamMsgIds, msg);
      return;
    }

    if (msg.type === 'team_result') {
      handleTeamResultEvent(set, get, _activeStreamMsgIds, msg);
      handleTeamResultMeta(set, msg);
      return;
    }

    if (msg.type === 'approval_request') {
      handleApprovalRequest(set, msg);
      return;
    }

    if (msg.type === 'thumbs') {
      handleThumbsEvent(set, msg);
    }
  };
}
