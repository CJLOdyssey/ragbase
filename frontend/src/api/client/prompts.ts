import api from './instance';

export interface PromptItem {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  content: string;
  model: string | null;
  status: string;
  version: string;
  created_at: string;
}

export async function listPrompts(): Promise<PromptItem[]> {
  const { data } = await api.get('/prompts');
  return data;
}

export async function createPrompt(payload: {
  name: string;
  description?: string;
  category: string;
  content: string;
  model?: string;
  status?: string;
}): Promise<PromptItem> {
  const { data } = await api.post('/prompts', payload);
  return data;
}

export async function updatePrompt(
  id: string,
  payload: Partial<{
    name: string;
    description: string;
    category: string;
    content: string;
    status: string;
  }>,
): Promise<PromptItem> {
  const { data } = await api.put(`/prompts/${id}`, payload);
  return data;
}

export async function deletePrompt(id: string): Promise<void> {
  await api.delete(`/prompts/${id}`);
}
