# 附件条上移 + 点击预览 — 设计文档

日期：2026-08-11
项目：agent-studio / ragbase（同步改动）

## 目标

1. 附件列表从输入框容器内（textarea 下方、模型下拉旁）**移到输入框上方独立附件条**，随输入框固定在页面底部。
2. 附件**提供预览**：图片显示缩略图，点击任意附件弹出预览面板（图片渲染 / 文本内容 / 不支持类型给下载入口）。

## 现状

- 两项目 `frontend/src/components/input/InputToolbar.tsx`：`<AttachmentList>` 渲染在 textarea 之后（输入框容器内底部，靠近模型下拉/附加文件按钮）。
- `AttachmentList.tsx` 显示：类型图标 + 文件名 + 大小 + 上传进度/失败态 + 删除按钮（`FileAttach` popover 与 `InputToolbar` 共用）。
- 后端已有 `/api/attachments/{id}` 下载接口（鉴权走 httpOnly cookie，`<img>` 标签可自动携带）。

## 设计

### 1. AttachmentList.tsx（改造，两项目同构）

- 图片（png/jpg/jpeg/gif/webp/svg）渲染 **40px 缩略图**：`<img src="/api/attachments/{attachmentId}">`，`object-fit: cover` 圆角；加载失败回退为图标；上传中显示占位图标+进度。
- 非图片保持图标+文件名+大小。
- 新增可选 `onPreview(f)` prop：点击附件触发；`FileAttach` 不传则维持现状（无预览、无点击行为）。

### 2. InputToolbar.tsx（改造）

- `<AttachmentList>` 移到输入框容器上方（`attach-bar`：flex-wrap 条，底部边框分隔）。
- 新增 `preview` state（`AttachedFile | null`），渲染 `AttachmentPreviewModal`。

### 3. AttachmentPreviewModal.tsx（新组件）

- 图片：大图渲染（点击遮罩 / ESC 关闭）。
- 文本（txt/md/json/log/csv/yaml 等）：`fetch("/api/attachments/{id}")` → `blob.text()` → 截断显示（前 64KB），加载态与失败态。
- PDF/其他：显示"暂不支持预览" + 下载按钮（`<a href="/api/attachments/{id}" download>`）。
- 头部：文件名 + 关闭按钮。

### 4. 测试（vitest）

- AttachmentList：图片渲染缩略图、非图片渲染图标、点击触发 `onPreview`、删除按钮。
- AttachmentPreviewModal：图片渲染、文本内容显示与截断、错误态。
- InputToolbar：附件条位于 textarea 上方（DOM 顺序断言）。

## 数据流

```
选择文件 → FileAttach 上传拿 attachmentId（现状不变）
→ files[] 状态（attachmentId, name, size, status）
→ AttachmentList 渲染（图片缩略图 img src=/api/attachments/{id}）
→ 点击 → AttachmentPreviewModal（fetch 下载接口预览文本 / img 大图 / 下载入口）
```

## 异常处理

- 缩略图加载失败 → 图标回退。
- 文本预览 fetch 失败 → 错误提示 + 下载按钮。
- 大文件文本预览 → 截断 64KB。
- 上传中附件（无 attachmentId）→ 不可点击预览。

## 改动文件（两项目各 4 个）

- `frontend/src/components/input/AttachmentList.tsx`（改造）
- `frontend/src/components/input/InputToolbar.tsx`（改造）
- `frontend/src/components/input/AttachmentPreviewModal.tsx`（新增）
- `frontend/src/components/input/__tests__/*`（新增/更新）
