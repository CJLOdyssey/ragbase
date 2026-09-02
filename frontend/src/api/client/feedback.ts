import api from './instance';

export async function createFeedback(
  runId: string,
  rating: 'good' | 'bad',
): Promise<{ id: string }> {
  const { data } = await api.post(`/runs/${runId}/feedback`, { rating });
  return data;
}
