# 附件条上移 + 点击预览 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把附件列表移到输入框上方独立附件条，并支持缩略图与点击预览（图片/文本/下载入口）。

**Architecture:** 纯前端改动。改造 `AttachmentList`（缩略图 + `onPreview` 可选 prop），新增 `AttachmentPreviewModal`（图片大图 / fetch 文本 / 下载入口），`InputToolbar` 把附件条移到 textarea 上方并持有 preview state。复用现有 `GET /api/attachments/{id}` 下载接口（httpOnly cookie 鉴权，`<img>` 自动携带）。

**Tech Stack:** React 18 + TypeScript + Tailwind 风格 CSS 变量 + vitest + @testing-library/react。

## Global Constraints

- **两个项目同步实现**：`agent-studio-same-issue-v2` 与 `ragbase-same-issue-v2`，每步在两项目都执行。
- 风格差异：agent-studio 紧凑单行 JSX；ragbase 为 prettier 多行格式（执行 ragbase 步骤后跑 `npm run format:check` / prettier 保持其约定）。逻辑代码完全相同。
- 缩略图与预览的图片扩展名白名单：`png|jpg|jpeg|gif|webp`（svg 排除——前端上传白名单即不含 svg，见 FileAttach ALLOWED_TYPES）。
- 文本预览扩展名：`txt|md|json|log|csv|yaml|yml`。
- 文本预览截断：前 64KB（`PREVIEW_CHAR_LIMIT = 64 * 1024`）。
- 下载/预览 URL 一律 `/api/attachments/{attachmentId}`（attachmentId 可能缺失：uploading/error 状态不可预览）。
- 组件文案用硬编码中文（与现有 AttachmentList「失败」文案一致，不引入 i18n 依赖）。
- 测试命令：`npm test -- --tagsFilter 'unit' --srcDir src` 不对——实际命令为 `npm test`（vitest run）；单文件：`npx vitest run <path>`。
- 遵守 AGENTS.md：代码获取优先 codegraph（本目录无索引 → 已用 read）；单文件 ≤400 行；不做无关改动。

---

### Task 1: AttachmentList 缩略图 + onPreview

**Files:**
- Modify: `frontend/src/components/input/AttachmentList.tsx`
- Modify: `frontend/src/components/input/__tests__/AttachmentList.test.tsx`

**Interfaces:**
- Produces: `AttachmentList({ files, onRemove, onPreview? })` — `onPreview?: (file: AttachedFile) => void`；图片附件（done + attachmentId）渲染 40px 缩略图 `img[src=/api/attachments/{attachmentId}]`；点击文件名区域（仅 done 且提供 onPreview 时是 button，aria-label `Preview {name}`）触发 `onPreview(file)`；删除按钮 `aria-label="Remove {name}"` 点击不触发预览。

- [ ] **Step 1: 写失败测试（agent-studio）**

在 `frontend/src/components/input/__tests__/AttachmentList.test.tsx` 末尾追加：

```tsx
describe('AttachmentList preview & thumbnails', { tags: ['unit'] }, () => {
  const imageFile = () =>
    makeFile('f1', {
      name: 'photo.png',
      type: 'image/png',
      status: 'done',
      attachmentId: 'att-1',
    });

  it('renders thumbnail for uploaded image', () => {
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} onPreview={vi.fn()} />
      </TestProviders>,
    );
    expect(screen.getByRole('img')).toHaveAttribute('src', '/api/attachments/att-1');
  });

  it('does not render thumbnail while uploading (no attachmentId)', () => {
    render(
      <TestProviders>
        <AttachmentList
          files={[makeFile('f1', { name: 'photo.png', type: 'image/png', status: 'uploading' })]}
          onRemove={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('falls back to icon when thumbnail fails to load', () => {
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} />
      </TestProviders>,
    );
    fireEvent.error(screen.getByRole('img'));
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('calls onPreview with the file when name button clicked', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} onPreview={onPreview} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Preview photo.png' }));
    expect(onPreview).toHaveBeenCalledWith(expect.objectContaining({ id: 'f1' }));
  });

  it('does not call onPreview when prop missing', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByText('photo.png'));
    expect(onPreview).not.toHaveBeenCalled();
  });

  it('remove button click does not trigger preview', () => {
    const onPreview = vi.fn();
    render(
      <TestProviders>
        <AttachmentList files={[imageFile()]} onRemove={vi.fn()} onPreview={onPreview} />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo.png' }));
    expect(onPreview).not.toHaveBeenCalled();
  });
});
```

顶部 imports 需要补 `fireEvent`：把 `import { render, screen } from '@testing-library/react';` 改为 `import { render, screen, fireEvent } from '@testing-library/react';`

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run frontend/src/components/input/__tests__/AttachmentList.test.tsx`（workdir `frontend`）
Expected: FAIL — `Unable to find role="img"`（缩略图测试失败），其余新测试同样失败。

- [ ] **Step 3: 实现（完整替换 AttachmentList.tsx）**

```tsx
import { useState } from 'react';
import { Image, FileText, File, X } from 'lucide-react';
import type { AttachedFile } from '../../types/input';

interface Props {
  files: AttachedFile[];
  onRemove: (id: string) => void;
  onPreview?: (file: AttachedFile) => void;
}

const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp)$/;

function getIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (IMAGE_EXT.test(ext || '')) return Image;
  if (/^(txt|md|doc|docx|pdf)$/.test(ext || '')) return FileText;
  return File;
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function isImage(name: string) {
  return IMAGE_EXT.test(name.split('.').pop()?.toLowerCase() || '');
}

/**
 * Shared attachment list — used by InputToolbar (attach bar above the textarea).
 * Thumbnails for uploaded images; optional onPreview makes the name a button.
 */
export default function AttachmentList({ files, onRemove, onPreview }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4">
      {files.map((f) => (
        <AttachmentChip key={f.id} file={f} onRemove={onRemove} onPreview={onPreview} />
      ))}
    </div>
  );
}

function AttachmentChip({
  file,
  onRemove,
  onPreview,
}: {
  file: AttachedFile;
  onRemove: (id: string) => void;
  onPreview?: (file: AttachedFile) => void;
}) {
  const [thumbFailed, setThumbFailed] = useState(false);
  const Icon = getIcon(file.name);
  const previewEnabled = !!onPreview && file.status === 'done';
  const showThumb =
    file.status === 'done' && !!file.attachmentId && isImage(file.name) && !thumbFailed;

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-md text-xs">
      {showThumb ? (
        <img
          src={`/api/attachments/${file.attachmentId}`}
          alt=""
          className="h-10 w-10 rounded object-cover"
          onError={() => setThumbFailed(true)}
        />
      ) : (
        <Icon size={14} />
      )}

      {previewEnabled ? (
        <button
          type="button"
          onClick={() => onPreview?.(file)}
          className="max-w-[240px] inline-flex items-center gap-1.5 bg-transparent border-none p-0 text-left cursor-pointer hover:underline"
          aria-label={`Preview ${file.name}`}
        >
          <span className="max-w-[120px] truncate text-[var(--color-text-primary)]">{file.name}</span>
          <span className="text-[var(--color-text-muted)] text-xs">{fmtSize(file.size)}</span>
        </button>
      ) : (
        <span className="inline-flex items-center gap-1.5">
          <span className="max-w-[120px] truncate text-[var(--color-text-primary)]">{file.name}</span>
          <span className="text-[var(--color-text-muted)] text-xs">{fmtSize(file.size)}</span>
        </span>
      )}

      {file.status === 'uploading' && (
        <span className="text-[var(--color-text-muted)] text-xs">{file.progress ?? 0}%</span>
      )}
      {file.status === 'error' && <span className="text-[var(--color-danger)] text-xs">失败</span>}
      <button
        type="button"
        className="p-0.5 bg-transparent border-none rounded text-[var(--color-text-muted)] cursor-pointer flex items-center justify-center hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
        onClick={(e) => {
          e.stopPropagation();
          onRemove(file.id);
        }}
        aria-label={`Remove ${file.name}`}
      >
        <X size={12} />
      </button>
    </span>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run frontend/src/components/input/__tests__/AttachmentList.test.tsx`（workdir `frontend`）
Expected: PASS（旧 12 用例 + 新 6 用例全部绿）

- [ ] **Step 5: ragbase 同改**

复制 Step 1 测试追加与 Step 3 实现到 ragbase 对应文件（ragbase 项目 run `npx prettier --write frontend/src/components/input/AttachmentList.tsx frontend/src/components/input/__tests__/AttachmentList.test.tsx` 以匹配其多行风格），跑 `npx vitest run frontend/src/components/input/__tests__/AttachmentList.test.tsx`（workdir `frontend`），Expected: PASS。

- [ ] **Step 6: Commit（两项目各自）**

```bash
git add frontend/src/components/input/AttachmentList.tsx frontend/src/components/input/__tests__/AttachmentList.test.tsx
git commit -m "feat: attachment thumbnails and optional preview callback"
```

---

### Task 2: AttachmentPreviewModal 新组件

**Files:**
- Create: `frontend/src/components/input/AttachmentPreviewModal.tsx`
- Create: `frontend/src/components/input/__tests__/AttachmentPreviewModal.test.tsx`

**Interfaces:**
- Consumes: `AttachedFile`（`@/types/input`），`/api/attachments/{attachmentId}` 下载接口
- Produces: `AttachmentPreviewModal({ file: AttachedFile; onClose: () => void })` — modal `role="dialog"`、`aria-label="Preview {name}"`；图片渲染 `img[src=/api/attachments/{id}]`；文本 fetch 后渲染 `<pre>`（截断 64KB）；未知类型显示「暂不支持预览该类型」+ 下载 `<a href={url} download>`；关闭：✕ 按钮（aria-label `Close preview`）/ ESC / 遮罩点击。

- [ ] **Step 1: 写失败测试（agent-studio）**

创建 `frontend/src/components/input/__tests__/AttachmentPreviewModal.test.tsx`：

```tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TestProviders } from '@/test/setup';
import AttachmentPreviewModal from '@/components/input/AttachmentPreviewModal';
import type { AttachedFile } from '@/types/input';

function makeFile(id: string, overrides: Partial<AttachedFile> = {}): AttachedFile {
  return {
    id,
    name: 'notes.md',
    size: 1024,
    type: 'text/markdown',
    status: 'done',
    attachmentId: 'att-1',
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('AttachmentPreviewModal', { tags: ['unit'] }, () => {
  it('renders image for image files', () => {
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/api/attachments/att-1');
  });

  it('fetches and renders text content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve({ text: () => Promise.resolve('hello world') }),
      }),
    );
    render(
      <TestProviders>
        <AttachmentPreviewModal file={makeFile('f1', { name: 'notes.md' })} onClose={vi.fn()} />
      </TestProviders>,
    );
    expect(await screen.findByText('hello world')).toBeInTheDocument();
  });

  it('shows loading state while fetching', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));
    render(
      <TestProviders>
        <AttachmentPreviewModal file={makeFile('f1', { name: 'notes.md' })} onClose={vi.fn()} />
      </TestProviders>,
    );
    expect(screen.getByText('加载中…')).toBeInTheDocument();
  });

  it('shows error and download link when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    render(
      <TestProviders>
        <AttachmentPreviewModal file={makeFile('f1', { name: 'notes.md' })} onClose={vi.fn()} />
      </TestProviders>,
    );
    expect(await screen.findByText('预览加载失败')).toBeInTheDocument();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/att-1');
    expect(link).toHaveAttribute('download');
  });

  it('truncates text longer than 64KB', async () => {
    const big = 'y'.repeat(70 * 1024);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve({ text: () => Promise.resolve(big) }),
      }),
    );
    const { container } = render(
      <TestProviders>
        <AttachmentPreviewModal file={makeFile('f1', { name: 'notes.md' })} onClose={vi.fn()} />
      </TestProviders>,
    );
    await waitFor(() => expect(container.querySelector('pre')).not.toBeNull());
    const pre = container.querySelector('pre')!;
    expect(pre.textContent).toContain('…');
    expect(pre.textContent!.length).toBeLessThan(70 * 1024);
    expect(pre.textContent!.includes('yyy')).toBe(false);
  });

  it('shows download button for unsupported type', () => {
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'archive.zip', type: 'application/zip' })}
          onClose={vi.fn()}
        />
      </TestProviders>,
    );
    expect(screen.getByText('暂不支持预览该类型')).toBeInTheDocument();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/api/attachments/att-1');
    expect(link).toHaveAttribute('download');
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={onClose}
        />
      </TestProviders>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose on Escape', () => {
    const onClose = vi.fn();
    render(
      <TestProviders>
        <AttachmentPreviewModal
          file={makeFile('f1', { name: 'photo.png', type: 'image/png' })}
          onClose={onClose}
        />
      </TestProviders>,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run frontend/src/components/input/__tests__/AttachmentPreviewModal.test.tsx`（workdir `frontend`）
Expected: FAIL — `Failed to resolve import "@/components/input/AttachmentPreviewModal"`

- [ ] **Step 3: 实现（创建 AttachmentPreviewModal.tsx）**

```tsx
import { useEffect, useState } from 'react';
import { Download, Loader2, X } from 'lucide-react';
import type { AttachedFile } from '../../types/input';

interface Props {
  file: AttachedFile;
  onClose: () => void;
}

const IMAGE_EXT = /^(png|jpg|jpeg|gif|webp)$/;
const TEXT_EXT = /^(txt|md|json|log|csv|yaml|yml)$/;
const PREVIEW_CHAR_LIMIT = 64 * 1024;

function getExt(name: string) {
  return name.split('.').pop()?.toLowerCase() || '';
}

/**
 * Modal preview for an attached file: image renders large, text is fetched
 * and shown (truncated), other types get a download link.
 */
export default function AttachmentPreviewModal({ file, onClose }: Props) {
  const ext = getExt(file.name);
  const isImage = IMAGE_EXT.test(ext);
  const isText = TEXT_EXT.test(ext);
  const url = `/api/attachments/${file.attachmentId}`;

  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(isText);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isText || !file.attachmentId) return;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    setText(null);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => blob.text())
      .then((content) => {
        if (cancelled) return;
        setText(content);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [url, isText, file.attachmentId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const truncated =
    text !== null && text.length > PREVIEW_CHAR_LIMIT
      ? `${text.slice(0, PREVIEW_CHAR_LIMIT)}\n\n…(内容过长，已截断)`
      : text;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Preview ${file.name}`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="max-w-3xl w-full max-h-[80vh] flex flex-col rounded-2xl bg-[var(--color-surface-raised)] border border-[var(--color-border)] shadow-2xl overflow-hidden">
        <header className="flex items-center justify-between gap-4 px-5 py-3 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
            {file.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close preview"
            className="p-1.5 bg-transparent border-none rounded-lg text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          >
            <X size={16} />
          </button>
        </header>

        <div className="flex-1 overflow-auto p-5">
          {isImage && (
            <img
              src={url}
              alt={file.name}
              className="mx-auto max-w-full max-h-[70vh] object-contain rounded-lg"
            />
          )}

          {isText && loading && (
            <div className="flex items-center justify-center gap-2 py-10 text-[var(--color-text-muted)] text-sm">
              <Loader2 size={18} className="animate-spin" />
              加载中…
            </div>
          )}

          {isText && failed && (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--color-danger)] mb-4">预览加载失败</p>
              <a
                href={url}
                download
                className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
              >
                <Download size={14} />
                下载文件
              </a>
            </div>
          )}

          {isText && text !== null && (
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--color-text-primary)]">
              {truncated}
            </pre>
          )}

          {!isImage && !isText && (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--color-text-muted)] mb-4">暂不支持预览该类型</p>
              <a
                href={url}
                download
                className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
              >
                <Download size={14} />
                下载文件
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run frontend/src/components/input/__tests__/AttachmentPreviewModal.test.tsx`（workdir `frontend`）
Expected: PASS（8 用例全绿）

- [ ] **Step 5: ragbase 同改**

复制 Step 1 测试与 Step 3 实现到 ragbase（run `npx prettier --write` 匹配多行风格），跑同测试命令，Expected: PASS。

- [ ] **Step 6: Commit（两项目各自）**

```bash
git add frontend/src/components/input/AttachmentPreviewModal.tsx frontend/src/components/input/__tests__/AttachmentPreviewModal.test.tsx
git commit -m "feat: attachment preview modal (image/text/download)"
```

---

### Task 3: InputToolbar 集成（附件条上移 + 预览弹窗）

**Files:**
- Modify: `frontend/src/components/input/InputToolbar.tsx`
- Modify: `frontend/src/components/input/__tests__/InputToolbar.test.tsx`

**Interfaces:**
- Consumes: `AttachmentList`（Task 1 的 `onPreview`），`AttachmentPreviewModal`（Task 2）
- Produces: `InputToolbar` 渲染：`<div data-testid="attach-bar">`（files 非空时）位于 textarea 之前；`previewFile` state 驱动 `AttachmentPreviewModal` 渲染在容器末尾。

- [ ] **Step 1: 写失败测试（agent-studio）**

在 `frontend/src/components/input/__tests__/InputToolbar.test.tsx` 末尾追加：

```tsx
describe('InputToolbar attachment bar & preview', { tags: ['unit'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUploadAttachment.mockResolvedValue({ id: 'att-1' });
    mockDeleteAttachment.mockResolvedValue({});
  });

  const addDoneFile = async (name = 'a.txt') => {
    const ref = createRef<InputToolbarHandle>();
    render(<InputToolbar {...defaultProps} ref={ref} />);
    act(() => {
      ref.current?.addFiles([new File(['content'], name)]);
    });
    await act(async () => {
      await Promise.resolve();
    });
  };

  it('renders attachment bar above the textarea', async () => {
    await addDoneFile();
    const textarea = screen.getByPlaceholderText('Type a message...');
    const bar = screen.getByTestId('attach-bar');
    expect(bar).toBeInTheDocument();
    expect(bar.compareDocumentPosition(textarea) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('does not render attachment bar when no files', () => {
    render(<InputToolbar {...defaultProps} />);
    expect(screen.queryByTestId('attach-bar')).toBeNull();
  });

  it('opens preview modal when attachment name clicked', async () => {
    await addDoneFile();
    fireEvent.click(screen.getByRole('button', { name: 'Preview a.txt' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('closes preview modal via close button', async () => {
    await addDoneFile();
    fireEvent.click(screen.getByRole('button', { name: 'Preview a.txt' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
```

顶部需补 import：`import { render, screen, fireEvent, act } from '@testing-library/react';` 已含全部；`createRef` 已 import。无需改其他 mock（Modal 不依赖任何被 mock 的模块；文本 fetch 在 jsdom 无实现时被 catch 吞掉——但为确定性，在 `addDoneFile` 后打开 modal 的用例中 fetch 会真实调用 Node fetch：被测文件 `a.txt` 属 TEXT_EXT，modal 打开即 fetch。**测试环境 Node 18+ 有 global fetch，会尝试真实请求并快速失败**，被 catch 捕获显示错误态——不影响 dialog 断言。若 CI 网络受限导致挂起，用 `vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no network')))` 于该 describe 的 beforeEach）。

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run frontend/src/components/input/__tests__/InputToolbar.test.tsx`（workdir `frontend`）
Expected: FAIL — `Unable to find an element with the test id: attach-bar`（新用例全失败，旧用例仍过）

- [ ] **Step 3: 实现（agent-studio）**

改 `frontend/src/components/input/InputToolbar.tsx`：

1. import 区加：`import AttachmentPreviewModal from './AttachmentPreviewModal';`（插在 `import AttachmentList from './AttachmentList';` 之后）

2. state 加（`const [files, setFiles] = ...` 之后一行）：

```tsx
const [previewFile, setPreviewFile] = useState<AttachedFile | null>(null);
```

3. 把 textarea 后的 `<AttachmentList files={files} onRemove={removeFile} />` 删除，改为在 `<textarea ... />` 之前（palette 块之后）插入：

```tsx
{files.length > 0 && (
  <div data-testid="attach-bar" className="pt-3 border-b border-[var(--color-border)]">
    <AttachmentList files={files} onRemove={removeFile} onPreview={setPreviewFile} />
  </div>
)}
```

4. `</div>`（input-wrapper 闭合）之后、`</motion.div>` 之前插入：

```tsx
{previewFile && (
  <AttachmentPreviewModal file={previewFile} onClose={() => setPreviewFile(null)} />
)}
```

（Modal 为 `fixed` 定位，放 motion.div 内部不影响布局。）

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run frontend/src/components/input/__tests__/InputToolbar.test.tsx`（workdir `frontend`）
Expected: PASS（旧 25 用例 + 新 4 用例全绿）

- [ ] **Step 5: ragbase 同改**

ragbase 的 `InputToolbar.tsx` 结构相同（prettier 多行格式 + import 排序：`AttachmentPreviewModal` 插在 `AttachmentList` 附近）。ragbase 的 `InputToolbar.test.tsx` import 已含 `fireEvent`/`act`/`createRef`；追加相同 describe。跑同测试命令（workdir `frontend`），Expected: PASS。ragbase run `npx prettier --write frontend/src/components/input/InputToolbar.tsx frontend/src/components/input/__tests__/InputToolbar.test.tsx` 保持风格。

- [ ] **Step 6: Commit（两项目各自）**

```bash
git add frontend/src/components/input/InputToolbar.tsx frontend/src/components/input/__tests__/InputToolbar.test.tsx
git commit -m "feat: move attachment bar above input and wire preview modal"
```

- [ ] **Step 7: 全量验证（两项目各自）**

Run（workdir `frontend`）：
```bash
npm run typecheck && npm test
```
Expected: 两命令均通过；`npm test` 无新增失败。再跑 `npm run lint`（workdir `frontend`），Expected: 无新增错误。

---

### 收尾

- [ ] 更新两项目 `docs/superpowers/specs/2026-08-11-attachment-preview-design.md` 状态（如适用：实现完成标注）
- [ ] 若需合并：`finishing-a-development-branch` 处理（当前留在 worktree 分支，等用户指示）
