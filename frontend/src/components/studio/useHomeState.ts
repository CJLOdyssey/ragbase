import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../auth';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import type { SessionItem } from '../../types';
import type { ModelOption } from '../../types/input';
import type { Message } from '../../types/studio';
import { listModels } from '../../api/client/models';
import { getSessionDetail, listSessions } from '../../api/client/sessions';
import { retry, submitRequirement } from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import {
  getSessionCache,
  MODEL_CHANGED_EVENT,
  MODEL_STORAGE_KEY,
  readActiveConvId,
  readSessionsCache,
  readStoredModel,
  setSessionCache,
  writeSessionsCache,
} from '../../stores/sessionCache';
import { useSessionOps } from './useSessionOps';
import {
  buildBranchPath,
  buildPathTurns,
  buildRunPath,
} from '../../utils/branchTurns';
import Logger from '../../utils/logger';
import { useSettings } from '../../contexts/SettingsContext';

export function useHomeState() {
  const { t } = useTranslation();
  const { settings, updateSettings } = useSettings();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const messages = useChatStore((s) => s.messages);
  const isRunning = useChatStore((s) => s.status === 'running');
  const cancelRun = useChatStore((s) => s.cancelRun);
  const apiStatus = useChatStore((s) => s.status);
  const apiError = useChatStore((s) => s.error);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isApiOpen, setIsApiOpen] = useState(false);
  // 会话标识单一事实源 = URL 路由 /chat/:sessionId（对齐 DeepSeek：可分享/
  // 收藏/多标签独立/前进后退）；localStorage 仅作 fallback（直达 / 时恢复）。
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const activeConvId = sessionId ?? null;
  // 会话加载中（恢复/切换，消息未就绪）— 期间渲染消息面板而非主页，
  // 避免刷新/点击后主页一闪而过。
  const [restoring, setRestoring] = useState<boolean>(
    () => sessionId !== undefined || readActiveConvId() !== null,
  );
  const [selectedModel, setSelectedModel] = useState(readStoredModel);
  const [recentModelIds, setRecentModelIds] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem('ragbase-recent-models');
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed)
        ? parsed.filter((x): x is string => typeof x === 'string')
        : [];
    } catch {
      return [];
    }
  });
  // 加载竞态保护：快速切换会话/分支时，丢弃过期响应（仅最新一次落地）。
  const loadSeqRef = useRef(0);

  useEffect(() => {
    const sync = () => {
      setSelectedModel(readStoredModel());
      try {
        const raw = localStorage.getItem('ragbase-recent-models');
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        setRecentModelIds(
          Array.isArray(parsed)
            ? parsed.filter((x): x is string => typeof x === 'string')
            : [],
        );
      } catch {
        // non-fatal
      }
    };
    window.addEventListener(MODEL_CHANGED_EVENT, sync);
    return () => window.removeEventListener(MODEL_CHANGED_EVENT, sync);
  }, []);

  // 首帧渲染缓存中的会话列表（同步），后台 API 返回后刷新覆盖。
  const [cachedSessions, setCachedSessions] =
    useState<SessionItem[]>(readSessionsCache);
  useQuery<SessionItem[]>({
    queryKey: ['sessions'],
    // 首帧渲染缓存，拉到最新列表后刷新缓存（queryFn 内落缓存，非 effect）。
    queryFn: async () => {
      const data = await listSessions();
      setCachedSessions(data);
      // 登出竞态守卫：invalidate 触发的 refetch 可能在登出后仍执行，
      // 不把登录用户会话写回 localStorage（登出已清缓存）。
      if (isAuthenticated) writeSessionsCache(data);
      return data;
    },
    // Sessions are user-owned: only fetch once authentication is ready, and
    // re-fetch when it flips (login/refresh completes after initial mount).
    enabled: isAuthenticated,
  });

  const { data: models = [] } = useQuery({
    queryKey: ['models'],
    // Backend returns 200 [] for unauthenticated GETs — only query once auth
    // is established so the pre-auth empty result is never cached.
    enabled: isAuthenticated,
    queryFn: async (): Promise<ModelOption[]> => {
      const infos = await listModels();
      return infos.map((m) => ({
        id: m.id,
        label: m.label,
        provider: m.provider,
      }));
    },
  });

  // 会话列表增删改（乐观本地覆盖 + 后端同步）与导航入口。
  const sessionOps = useSessionOps({
    cachedSessions,
    setCachedSessions,
    activeConvId,
    setRestoring,
  });

  // 退出登录：重置模型选择、清空会话列表、失效会话/模型查询并回首页
  // （登出已清 store/localStorage，这里清组件内 useState + 查询缓存 —
  // '/' 与 '/chat/:id' 同组件，navigate 不会卸载重置）。
  useEffect(() => {
    const onLogout = () => {
      setSelectedModel('');
      setCachedSessions([]);
      // sessions 缓存直接移除（不 invalidate，避免登出瞬间 refetch 把
      // 登录用户会话写回 localStorage）；models 无本地缓存，invalidate 即可。
      queryClient.removeQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
      navigate('/');
    };
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, [queryClient, navigate]);

  const displayMessages: Message[] = useMemo(
    () =>
      messages.map((m) => ({
        id: m.id,
        role: m.role === 'user' ? 'user' : 'agent',
        content: m.content,
        thinking: m.thinking,
        answer: m.content,
        thinkingDone: m.thinkingDone,
        userVersions: m.userVersions,
        currentUserVersion: m.currentUserVersion,
        answerVersions: m.answerVersions,
        currentAnswerVersion: m.currentAnswerVersion,
        userMsgId: m.userMsgId,
        runId: m.runId,
        attachments: m.attachments,
      })),
    [messages],
  );

  const hasMessages = displayMessages.length > 0;
  const effectiveModel = useMemo(() => {
    if (selectedModel) return selectedModel;
    // 未显式选择时，默认取用户最近使用过的模型（recent-models 顶部第一个）。
    const recent = recentModelIds.find((id) => models.some((m) => m.id === id));
    return recent || '';
  }, [selectedModel, models, recentModelIds]);

  const handleSend = useCallback(
    async (
      text: string,
      files?: import('../../types/input').AttachedFile[],
    ) => {
      if (!text.trim()) return;
      // 附件已由 InputToolbar 选中即传（pre-session），这里只带已上传的 id
      const ids = files
        ?.map((f) => f.attachmentId)
        .filter((x): x is string => !!x);
      await submitRequirement(
        text,
        undefined,
        undefined,
        undefined,
        undefined,
        ids?.length ? ids : undefined,
        files
          ?.filter((f) => f.attachmentId)
          .map((f) => ({ id: f.attachmentId as string, filename: f.name })),
      );
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
    [queryClient],
  );

  const handleModelChange = useCallback((id: string) => {
    setSelectedModel(id);
    try {
      localStorage.setItem(MODEL_STORAGE_KEY, id);
    } catch {
      // storage unavailable — in-memory selection still applies
    }
    window.dispatchEvent(new Event(MODEL_CHANGED_EVENT));
  }, []);

  const loadConversationById = useCallback(async (convId: string) => {
    setRestoring(true);
    // 切换即时性（stale-while-revalidate）：已加载过的会话先渲染缓存（毫秒级），
    // 网络详情返回后再覆盖（后端为准）。首次无缓存才需要等待网络。
    const cached = getSessionCache(convId);
    if (cached) {
      useChatStore.getState().loadConversation(cached.loaded, convId);
      useChatStore.getState().setActiveRunId(cached.active);
    } else {
      // 首次加载无缓存 — 立即清空旧会话消息，避免残留跳变。
      useChatStore.getState().clearMessages();
    }
    const seq = ++loadSeqRef.current;
    try {
      const detail = await getSessionDetail(convId);
      if (seq !== loadSeqRef.current) return;
      const { path, active } = buildRunPath(detail.runs ?? []);
      const loaded = buildPathTurns(path, detail.runs ?? []);
      // Persisted messages are completed turns — mark agent thinking as done
      // so the ThinkingSection shows "已思考" instead of a stuck spinner.
      for (const m of loaded) {
        if (m.role !== 'user' && m.thinkingDone === undefined) {
          m.thinkingDone = true;
        }
      }
      setSessionCache(convId, { loaded, active });
      useChatStore.getState().loadConversation(loaded, convId);
      useChatStore.getState().setActiveRunId(active);
      Logger.info(
        '[loadConv] conv=%s runs=%d path=%d loaded=%d lastRun=%s',
        convId.slice(0, 8),
        (detail.runs ?? []).length,
        path.length,
        loaded.length,
        active?.slice(0, 8) ?? '-',
      );
    } catch (err) {
      Logger.warn('[useHomeState] failed to load conversation', err);
    }
    if (seq === loadSeqRef.current) {
      setRestoring(false);
    }
  }, []);

  // 会话路由驱动：进入/切换/前进后退（URL 变化）→ 加载对应会话；
  // URL 无会话（主页）→ 清空消息。setTimeout 延后一帧：加载开始的同步
  // setState（restoring）移出 effect 体（react-hooks/set-state-in-effect），
  // 竞态仍由 loadSeqRef 兜底。
  useEffect(() => {
    if (activeConvId) {
      const timer = setTimeout(() => {
        void loadConversationById(activeConvId);
      }, 0);
      return () => clearTimeout(timer);
    }
    useChatStore.getState().reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConvId]);

  // 直达主页（无 URL 会话）时恢复上次会话：localStorage fallback 后
  // 以 URL 形式重建（replace，不堆历史）。
  useEffect(() => {
    const stored = readActiveConvId();
    if (!sessionId && stored) {
      navigate(`/chat/${stored}`, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 分支语义：切版本 = 切分支，视图整体切到目标 run 所在分支的全部消息
  // （父链 + 子孙链，后续轮次跟随目标分支；不在该分支的轮次仅视图隐藏，DB 留存）。
  const handleSwitchBranch = useCallback(async (runId: string) => {
    // currentSessionId 即当前会话 id（loadConversation 与流式提交均设置；
    // 历史 currentConvId 已合并至此字段）。
    const convId = useChatStore.getState().currentSessionId;
    if (!convId) return;
    const seq = ++loadSeqRef.current;
    try {
      const detail = await getSessionDetail(convId);
      if (seq !== loadSeqRef.current) return;
      const currentPath = new Set(
        useChatStore
          .getState()
          .messages.map((m) => m.runId)
          .filter((id): id is string => !!id),
      );
      const path = buildBranchPath(detail.runs ?? [], runId, currentPath);
      const loaded = buildPathTurns(path, detail.runs ?? []);
      for (const m of loaded) {
        if (m.role !== 'user' && m.thinkingDone === undefined) {
          m.thinkingDone = true;
        }
      }
      useChatStore.getState().loadConversation(loaded, convId);
      // activeRunId 设为加载分支的末端（buildBranchPath 可能经 tail 选择了
      // 平行分支），后续追问才挂到当前显示的分支而非传入的父节点。
      useChatStore
        .getState()
        .setActiveRunId(path[path.length - 1]?.id ?? runId);
      Logger.info(
        '[switchBranch] run=%s runs=%d path=%d loaded=%d',
        runId.slice(0, 8),
        (detail.runs ?? []).length,
        path.length,
        loaded.length,
      );
    } catch (err) {
      Logger.warn('[useHomeState] failed to switch branch to %s', runId, err);
    }
  }, []);

  return {
    t,
    settings,
    updateSettings,
    isDarkMode: settings.theme === 'dark',
    conversations: sessionOps.conversations,
    activeConvId,
    setActiveConvId: sessionOps.handleSelectConversation,
    displayMessages,
    // activeConvId 非空（URL 指向会话）→ 恒显示消息面板：加载中 restoring
    // 保真，空会话（runs 为空）也停驻空面板而非回弹主页。
    hasMessages: hasMessages || restoring || activeConvId !== null,
    models,
    selectedModel: effectiveModel,
    setSelectedModel: handleModelChange,
    handleSend,
    handleStop: cancelRun,
    handleNewChat: sessionOps.handleNewChat,
    handleSwitchBranch,
    handleDeleteConversation: sessionOps.handleDeleteConversation,
    handleRenameConversation: sessionOps.handleRenameConversation,
    handlePinConversation: sessionOps.handlePinConversation,
    isSidebarOpen,
    setIsSidebarOpen,
    isUserMenuOpen,
    setIsUserMenuOpen,
    isSettingsOpen,
    setIsSettingsOpen,
    isApiOpen,
    setIsApiOpen,
    isRunning,
    apiStatus,
    apiError,
    retryApi: retry,
  };
}
