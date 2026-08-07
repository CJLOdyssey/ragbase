import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ModelOption } from '../../types/input';
import type { Conversation, Message } from '../../types/studio';
import { listModels } from '../../api/client/models';
import { listSessions } from '../../api/client/sessions';
import { submitRequirement } from '../../stores/chatActions';
import { useChatStore } from '../../stores/chatStore';
import { useSettings } from '../../contexts/SettingsContext';

export function useHomeState() {
  const { t } = useTranslation();
  const { settings, updateSettings } = useSettings();
  const messages = useChatStore((s) => s.messages);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isApiOpen, setIsApiOpen] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState('');

  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => listSessions(),
  });

  const { data: models = [] } = useQuery({
    queryKey: ['models'],
    queryFn: async (): Promise<ModelOption[]> => {
      const infos = await listModels();
      return infos.map((m) => ({
        id: m.id,
        label: m.label,
        provider: m.provider,
      }));
    },
  });

  const conversations: Conversation[] = useMemo(
    () =>
      sessions.map((s) => ({
        id: s.id,
        title: s.title,
        createdAt: s.created_at || '',
        updatedAt: s.updated_at || '',
        lastMessage: '',
        messages: [],
      })),
    [sessions],
  );

  const displayMessages: Message[] = useMemo(
    () =>
      messages.map((m) => ({
        id: m.id,
        role: m.role === 'user' ? 'user' : 'agent',
        content: m.content,
        thinking: m.thinking,
        answer: m.content,
      })),
    [messages],
  );

  const hasMessages = displayMessages.length > 0;
  const effectiveModel = selectedModel || models[0]?.id || '';
  const isRunning = false;

  const handleSend = useCallback((text: string) => {
    if (!text.trim()) return;
    void submitRequirement(text);
  }, []);

  const handleNewChat = useCallback(() => {
    useChatStore.getState().reset();
    setActiveConvId(null);
  }, []);

  const handleDeleteConversation = useCallback(
    (convId: string) => {
      if (activeConvId === convId) {
        useChatStore.getState().reset();
        setActiveConvId(null);
      }
    },
    [activeConvId],
  );

  return {
    t,
    settings,
    updateSettings,
    isDarkMode: settings.theme === 'dark',
    conversations,
    activeConvId,
    setActiveConvId,
    displayMessages,
    hasMessages,
    models,
    selectedModel: effectiveModel,
    setSelectedModel,
    handleSend,
    handleNewChat,
    handleDeleteConversation,
    isSidebarOpen,
    setIsSidebarOpen,
    isUserMenuOpen,
    setIsUserMenuOpen,
    isSettingsOpen,
    setIsSettingsOpen,
    isApiOpen,
    setIsApiOpen,
    isRunning,
  };
}
