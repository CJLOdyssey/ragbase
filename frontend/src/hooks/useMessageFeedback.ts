import { useCallback } from 'react';
import { createFeedback } from '../api/client/feedback';
import { useChatStore } from '../stores/chatStore';
import Logger from '../utils/logger';
import { useToast } from '../utils/useToast';
import i18n from '../i18n';

/**
 * 消息反馈提交流程（SoC：数据获取/提交收敛到 hook，组件只做展示编排）。
 * 负责：本地点赞态更新 + 后端 createFeedback 提交 + 结果/失败提示。
 */
export function useMessageFeedback() {
  const setThumbsFeedback = useChatStore((s) => s.setThumbsFeedback);
  const { toast } = useToast();

  return useCallback(
    (msgId: string, value: 'up' | 'down' | null) => {
      setThumbsFeedback(msgId, value);
      if (value) {
        const msg = useChatStore
          .getState()
          .messages.find((m) => m.id === msgId);
        const runId = msg?.runId;
        if (runId) {
          const rating = value === 'up' ? 'good' : 'bad';
          createFeedback(runId, rating)
            .then(() => {
              toast(i18n.t('feedback.feedbackNotice'), 'success');
            })
            .catch((err) =>
              Logger.warn('[feedback] failed to submit: %s', err),
            );
        }
      }
    },
    [setThumbsFeedback, toast],
  );
}