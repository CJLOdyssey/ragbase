import api from './instance';

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  session_id?: string | null;
  run_id?: string | null;
  has_extracted_text: boolean;
  created_at: string;
}

/**
 * Upload a single file. session_id is optional: pre-session uploads (first
 * message carries files before any session exists) are user-scoped and bound
 * to the run when the message is submitted.
 */
export async function uploadAttachment(
  file: File,
  session_id?: string | null,
  run_id?: string | null,
  onProgress?: (percent: number) => void,
  signal?: AbortSignal,
): Promise<Attachment> {
  const form = new FormData();
  form.append('file', file);
  if (session_id) form.append('session_id', session_id);
  if (run_id) form.append('run_id', run_id);
  const { data } = await api.post('/attachments', form, {
    // 覆盖实例默认的 application/json：否则 axios 会把 FormData 序列化成
    // JSON 字符串（{"file":{}}），后端 multipart 解析 422。置 undefined 让
    // axios 走 FormData 分支自动设置 multipart boundary。
    headers: { 'Content-Type': undefined },
    onUploadProgress: (e) => {
      if (onProgress && e.total)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
    signal,
  });
  return data;
}

export async function deleteAttachment(attachmentId: string): Promise<void> {
  await api.delete(`/attachments/${attachmentId}`);
}
