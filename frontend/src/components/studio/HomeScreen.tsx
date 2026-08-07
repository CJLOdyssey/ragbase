import type { RefObject } from 'react';
import { InputToolbar, type InputToolbarHandle } from '../input';
import {
  BarChart3,
  Bot,
  FileText,
  Image,
  MoreHorizontal,
  Search,
} from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import type {
  AttachedFile,
  CommandOption,
  ModelOption,
} from '../../types/input';
import GreetingAnimation from './GreetingAnimation';

interface Props {
  conversationKey: number;
  models: ModelOption[];
  selectedModel: string;
  onModelChange: (id: string) => void;
  commands: CommandOption[];
  onSend: (text: string, files: AttachedFile[]) => void;
  onExecuteCommand?: (commandId: string) => void;
  onConfigureModels?: () => void;
  inputToolbarRef: RefObject<InputToolbarHandle>;
  isRunning?: boolean;
  onStop?: () => void;
}

export default function HomeScreen({
  conversationKey,
  models,
  selectedModel,
  onModelChange,
  commands,
  onSend,
  onExecuteCommand,
  onConfigureModels,
  inputToolbarRef,
  isRunning,
  onStop,
}: Props) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-0">
      <div className="w-full max-w-[900px] flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center w-full">
          <div className="text-center mb-8">
            <div
              className="w-[72px] h-[72px] mx-auto mb-6 bg-[var(--color-surface-raised)] rounded-xl flex items-center justify-center"
              role="img"
              tabIndex={-1}
              aria-label="AgentStudio Logo"
            >
              <Bot size={48} className="text-[var(--color-accent)]" />
            </div>
            <GreetingAnimation key={conversationKey} />
            <p className="text-base text-[var(--color-text-muted)] m-0">
              {t('home.subtitle')}
            </p>
          </div>
          <InputToolbar
            ref={inputToolbarRef}
            onSend={onSend}
            models={models}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            placeholder={t('home.placeholder')}
            commands={commands}
            onExecuteCommand={onExecuteCommand}
            onConfigureModels={onConfigureModels}
            isRunning={isRunning}
            onStop={onStop}
          />
          <motion.div
            className="flex items-center justify-center gap-2 mt-4 flex-wrap"
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.4 }}
          >
            <motion.button
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-[var(--color-border)] rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 whitespace-nowrap hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)]"
              onClick={() => onExecuteCommand?.('search')}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.25 }}
            >
              <Search size={16} />
              <span>{t('features.search', '搜索')}</span>
            </motion.button>
            <motion.button
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-[var(--color-border)] rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 whitespace-nowrap hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)]"
              onClick={() => onExecuteCommand?.('data')}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.25 }}
            >
              <BarChart3 size={16} />
              <span>{t('features.data', '数据')}</span>
            </motion.button>
            <motion.button
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-[var(--color-border)] rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 whitespace-nowrap hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)]"
              onClick={() => onExecuteCommand?.('document')}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.25 }}
            >
              <FileText size={16} />
              <span>{t('features.document', '文档')}</span>
            </motion.button>
            <motion.button
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-[var(--color-border)] rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 whitespace-nowrap hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)]"
              onClick={() => onExecuteCommand?.('image')}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55, duration: 0.25 }}
            >
              <Image size={16} />
              <span>{t('features.image', '图片')}</span>
            </motion.button>
            <motion.button
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-[var(--color-border)] rounded-md text-[var(--color-text-secondary)] text-sm cursor-pointer transition-colors duration-150 whitespace-nowrap hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)]"
              onClick={() => onExecuteCommand?.('more')}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.25 }}
            >
              <MoreHorizontal size={16} />
              <span>{t('features.more', '更多')}</span>
            </motion.button>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
