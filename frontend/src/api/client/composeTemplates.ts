import type { ComposeTemplate } from '../../types/generation';
import api from './instance';

export async function listComposeTemplates(): Promise<ComposeTemplate[]> {
  const { data } = await api.get('/compose-templates');
  return data;
}
