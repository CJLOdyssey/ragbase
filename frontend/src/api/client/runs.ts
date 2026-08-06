import api from './instance';

export async function submitRequirement(
  requirement: string,
  session_id?: string,
  key_id?: string,
  model?: string,
  agent_id?: string,
  team_id?: string,
  parent_run_id?: string,
): Promise<{ run_id: string; status: string; session_id?: string }> {
  const { data } = await api.post('/runs', {
    requirement,
    session_id,
    key_id: key_id || undefined,
    model: model || undefined,
    agent_id: agent_id || undefined,
    team_id: team_id || undefined,
    parentRunId: parent_run_id || undefined,
  });
  return data;
}

export async function resumeRun(
  content: string,
  session_id?: string,
  thinking?: string,
): Promise<{ run_id: string; status: string; session_id?: string }> {
  const { data } = await api.post('/runs/complete', {
    content,
    session_id,
    thinking: thinking || undefined,
  });
  return data;
}
