import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import type * as React from 'react';
import { Send, Square } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import type {
  AttachedFile,
  CommandOption,
  FileRejection,
  ModelOption,
} from '../../types/input';
import {
  deleteAttachment,
  uploadAttachment,
} from '../../api/client/attachments';
import AttachmentList from './AttachmentList';
import AttachmentPreviewModal from './AttachmentPreviewModal';
import CommandDropdown from './CommandDropdown';
import FileAttach from './FileAttach';
import ModelSelector from './ModelSelector';
import PromptSelector from './PromptSelector';
import SessionKBSelector from './SessionKBSelector';
import { useCommandPalette } from '../../hooks/useCommandPalette';
import { useMessageComposer } from '../../hooks/useMessageComposer';
import { useToast } from '../../utils/useToast';
import { useSettings } from '../../contexts/SettingsContext';

export interface InputToolbarHandle {
  addFiles: (files: File[]) => void;
  /** 外部注入输入框内容（会话选中填充标题等场景） */
  setValue: (v: string) => void;
}

interface InputToolbarProps {
  onSend: (text: string, files: AttachedFile[]) => void;
  models: ModelOption[];
  selectedModel: string;
  onModelChange: (id: string) => void;
  onConfigureModels?: () => void;
  onExecuteCommand?: (commandId: string) => void;
  commands?: CommandOption[];
  placeholder?: string;
  maxLength?: number;
  /** Show stop button instead of send button (interrupt streaming) */
  isRunning?: boolean;
  /** Called when stop button is clicked */
  onStop?: () => void;
  /** Session ID for KB binding */
  sessionId?: string | null;
  /** Knowledge base IDs bound to the current session */
  knowledgeBaseIds?: string[];
  /** Called when KB selection changes */
  onKBChange?: (ids: string[]) => void;
}

const MAX_FILES = 5;

const InputToolbar = forwardRef<InputToolbarHandle, InputToolbarProps>(
  function InputToolbar(
    {
      onSend,
      models,
      selectedModel,
      onModelChange,
      onConfigureModels,
      onExecuteCommand,
      commands = [],
      placeholder,
      maxLength = 10000,
      isRunning = false,
      onStop,
      sessionId,
      knowledgeBaseIds = [],
      onKBChange,
    },
    ref,
  ) {
    const { t } = useTranslation();
    const reduce = useReducedMotion();
    const { toast } = useToast();
    const [files, setFiles] = useState<AttachedFile[]>([]);
    const [previewFile, setPreviewFile] = useState<AttachedFile | null>(null);
    const { settings } = useSettings();
    const abortControllersRef = useRef<Map<string, AbortController>>(new Map());

    const composer = useMessageComposer({
      onSend: (text) => {
        // 附件未就绪（上传中/失败）时不发送——失败需移除，进行中需等待
        const pending = files.filter((f) => f.status !== 'done');
        if (pending.length > 0) {
          const allFailed = pending.every((f) => f.status === 'error');
          toast(
            allFailed
              ? t(
                  'home.uploadFailed',
                  'Some files failed to upload, remove and retry',
                )
              : t('home.uploading', 'Uploading files, please wait'),
            'error',
          );
          return;
        }
        onSend(text, files);
        setFiles([]);
      },
      maxLength,
      sendMode: settings.sendMode,
    });

    // ── Slash-command palette ──

    // 清理未完成的上传 AbortController（组件卸载时取消所有进行中的请求）
    useEffect(() => {
      const controllers = abortControllersRef.current;
      return () => {
        controllers.forEach((ctrl) => ctrl.abort());
        controllers.clear();
      };
    }, []);

    const palette = useCommandPalette(commands);

    const handleCommandSelect = useCallback(
      (index: number) => {
        if (index < 0 || index >= palette.filtered.length) return;
        const cmd = palette.filtered[index];
        if (cmd.source === 'local' && onExecuteCommand) {
          palette.close();
          onExecuteCommand(cmd.id);
          return;
        }
        const replacement = palette.selectCommand(index, composer.value);
        if (replacement) composer.setValue(replacement);
      },
      [palette, composer, onExecuteCommand],
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Let palette intercept first (arrow keys, Enter, Escape when open)
        const handled = palette.handleKeyDown(e, composer.value);
        if (handled) {
          if (e.key === 'Enter' && !e.shiftKey && palette.open) {
            handleCommandSelect(palette.activeIndex);
          }
          return;
        }
        // Fall through to composer (Enter to send, etc.)
        composer.handleKeyDown(e);
      },
      [palette, composer, handleCommandSelect],
    );

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        composer.setValue(e.target.value);
        palette.updateFromValue(e.target.value);
      },
      [composer, palette],
    );

    // ── File handling ──

    // 选中即传（行业模式）：文件上传与会话解耦（后端支持 pre-session 上传），
    // 选中立刻上传拿 attachment id，发送时消息只带 id。
    const addFiles = useCallback(
      (incoming: File[]) => {
        const now = Date.now();
        const all: AttachedFile[] = incoming.map((f, i) => ({
          id: `${now}-${i}-${Math.random().toString(36).slice(2, 6)}`,
          name: f.name,
          size: f.size,
          type: f.type,
          file: f,
          status: 'uploading',
          progress: 0,
        }));
        const room = MAX_FILES - files.length;
        if (room < all.length) {
          toast(t('home.maxFiles', { count: MAX_FILES }), 'info');
        }
        const toKeep = all.slice(0, Math.max(0, room));
        setFiles((prev) => [...prev, ...toKeep]);
        for (const m of toKeep) {
          if (!m.file) continue;
          const controller = new AbortController();
          abortControllersRef.current.set(m.id, controller);
          uploadAttachment(
            m.file,
            undefined,
            undefined,
            (pct) => {
              setFiles((prev) =>
                prev.map((x) =>
                  x.id === m.id ? { ...x, progress: pct } : x,
                ),
              );
            },
            controller.signal,
          )
            .then((att) => {
              abortControllersRef.current.delete(m.id);
              setFiles((prev) =>
                prev.map((x) =>
                  x.id === m.id
                    ? { ...x, status: 'done', attachmentId: att.id }
                    : x,
                ),
              );
            })
            .catch((err) => {
              abortControllersRef.current.delete(m.id);
              // 忽略 AbortError（组件卸载时取消的请求）
              if (err?.name === 'CanceledError' || err?.name === 'AbortError')
                return;
              setFiles((prev) =>
                prev.map((x) =>
                  x.id === m.id ? { ...x, status: 'error' } : x,
                ),
              );
            });
        }
      },
      [toast, t, files],
    );

    const removeFile = useCallback((id: string) => {
      // 取消进行中的上传请求
      const controller = abortControllersRef.current.get(id);
      if (controller) {
        controller.abort();
        abortControllersRef.current.delete(id);
      }
      setFiles((prev) => {
        const target = prev.find((f) => f.id === id);
        if (target?.attachmentId) {
          deleteAttachment(target.attachmentId).catch(() => {
            /* orphan server file — best effort cleanup */
          });
        }
        return prev.filter((f) => f.id !== id);
      });
    }, []);

    useImperativeHandle(
      ref,
      () => ({
        addFiles,
        setValue: (v: string) => {
          composer.setValue(v);
          palette.updateFromValue(v);
        },
      }),
      [addFiles, composer, palette],
    );

    const handleReject = useCallback(
      (rejections: FileRejection[]) => {
        for (const r of rejections) {
          if (r.reason === 'size_exceeded') {
            toast(t('home.fileTooLarge', { name: r.file.name }), 'error');
          } else {
            toast(t('home.fileTypeDenied', { name: r.file.name }), 'error');
          }
        }
      },
      [toast, t],
    );

    const handlePaste = useCallback(
      (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
        if (e.clipboardData.files.length > 0) {
          e.preventDefault();
          addFiles(Array.from(e.clipboardData.files));
        }
      },
      [addFiles],
    );

    return (
      <motion.div
        className="box-border shrink-0 px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-3 max-w-[900px] mx-auto w-full md:px-6 md:pb-5 md:pt-4"
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      >
        {files.length > 0 && (
          <div
            data-testid="attach-bar"
            className="mb-2 px-4 pt-3 pb-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--da-input-radius)]"
          >
            <AttachmentList
              files={files}
              onRemove={removeFile}
              onPreview={setPreviewFile}
            />
          </div>
        )}

        <div
          data-input-wrapper
          className="relative bg-[var(--color-surface-raised)] border-none rounded-[var(--da-input-radius)] transition-shadow duration-200 shadow-none focus-within:shadow-[0 0 0 2px var(--color-accent)]"
        >
          {palette.open && (
            <CommandDropdown
              commands={palette.filtered}
              activeIndex={palette.activeIndex}
              onSelect={handleCommandSelect}
              onHover={palette.setActiveIndex}
              onClose={palette.close}
            />
          )}

          <textarea
            className="w-full bg-transparent border-none px-4 py-4 md:px-6 md:py-5 min-h-[var(--da-input-height)] max-h-[200px] resize-none text-base md:text-lg font-normal text-[var(--color-text-primary)] leading-[1.5] box-border scrollbar-thin scrollbar-thumb-transparent hover:scrollbar-thumb-[var(--color-border)] placeholder:text-[var(--color-text-muted)] placeholder:font-normal"
            style={{ outline: 'none' }}
            placeholder={placeholder ?? t('home.placeholder')}
            value={composer.value}
            maxLength={maxLength}
            aria-label={placeholder ?? t('home.placeholder')}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
          />

          <div className="flex items-center justify-between gap-1 py-2 px-2 sm:px-4 sm:py-3 bg-[var(--color-surface-raised)] border-t-0 min-h-[var(--da-toolbar-height)] rounded-b-[var(--da-input-radius)]">
            <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 shrink">
              <ModelSelector
                models={models}
                selectedModel={selectedModel}
                onChange={onModelChange}
                onConfigure={onConfigureModels}
              />
              <SessionKBSelector
                sessionId={sessionId ?? null}
                knowledgeBaseIds={knowledgeBaseIds}
                onChange={onKBChange ?? (() => {})}
              />
              <PromptSelector />
              <FileAttach
                onAdd={addFiles}
                onReject={handleReject}
                fileCount={files.length}
              />
            </div>

            <div className="shrink-0">
              {isRunning ? (
                <button
                  onClick={onStop}
                  className="flex items-center justify-center gap-2 px-3 sm:px-4 md:px-6 py-2 rounded-xl border-none text-sm sm:text-base font-semibold cursor-pointer transition-all duration-150 min-h-10 bg-red-500/20 text-[var(--color-danger)] shadow-sm hover:bg-red-500/30 hover:-translate-y-px hover:shadow-md active:translate-y-0 active:shadow-sm"
                  aria-label={t('home.stop')}
                >
                  <Square size={14} fill="currentColor" />
                  <span className="hidden sm:inline">{t('home.stop')}</span>
                </button>
              ) : (
                <button
                  onClick={composer.submit}
                  disabled={!composer.hasContent}
                  className={`flex items-center justify-center gap-2 px-3 sm:px-4 md:px-6 py-2 rounded-xl border-none text-sm sm:text-base font-semibold cursor-pointer transition-all duration-150 min-h-10 ${
                    composer.hasContent
                      ? 'bg-[var(--color-accent)] text-[var(--color-text-on-accent)] shadow-sm hover:brightness-115 hover:-translate-y-px hover:shadow-md active:translate-y-0 active:shadow-sm'
                      : 'bg-[var(--color-surface-hover)] text-[var(--color-text-muted)] cursor-not-allowed opacity-70'
                  }`}
                  aria-label={t('home.send')}
                >
                  <span className="hidden md:inline">{t('home.send')}</span>
                  <Send size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
        {previewFile && (
          <AttachmentPreviewModal
            file={previewFile}
            onClose={() => setPreviewFile(null)}
          />
        )}
      </motion.div>
    );
  },
);

export default InputToolbar;
