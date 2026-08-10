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
): Promise<Attachment> {
  const form = new FormData();
  form.append('file', file);
  if (session_id) form.append('session_id', session_id);
  if (run_id) form.append('run_id', run_id);
  const { data } = await api.post('/attachments', form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total)
        onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function uploadAttachments(
  files: File[],
  session_id?: string | null,
  run_id?: string | null,
): Promise<Attachment[]> {
  return Promise.all(files.map((f) => uploadAttachment(f, session_id, run_id)));
}

export async function deleteAttachment(attachmentId: string): Promise<void> {
  await api.delete(`/attachments/${attachmentId}`);
}
