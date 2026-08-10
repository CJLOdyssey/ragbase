import api from './instance';

export async function submitRequirement(
  requirement: string,
  session_id?: string,
  key_id?: string,
  model?: string,
  parent_run_id?: string | null,
  attachment_ids?: string[],
): Promise<{ run_id: string; status: string; session_id?: string }> {
  const { data } = await api.post('/runs', {
    requirement,
    session_id,
    key_id: key_id || undefined,
    model: model || undefined,
    parent_run_id: parent_run_id || undefined,
    attachment_ids: attachment_ids?.length ? attachment_ids : undefined,
  });
  return data;
}

export async function resumeRun(
  content: string,
  session_id?: string,
  thinking?: string,
  model?: string,
  question?: string,
): Promise<{ run_id: string; status: string; session_id?: string }> {
  const { data } = await api.post('/runs/complete', {
    content,
    session_id,
    thinking: thinking || undefined,
    model: model || undefined,
    question: question || undefined,
  });
  return data;
}

export async function cancelRun(
  runId: string,
): Promise<{ run_id: string; status: string; session_id?: string }> {
  const { data } = await api.post(`/runs/${runId}/cancel`);
  return data;
}
