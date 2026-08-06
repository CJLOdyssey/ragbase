import type {
  ComposeCardResult,
  ComposeRequest,
  GenerationCreateRequest,
  GenerationDetail,
  GenerationResponse,
  ImageGenerateRequest,
  ImageResult,
} from '../../types/generation';
import api from './instance';

export async function createGeneration(
  req: GenerationCreateRequest,
): Promise<GenerationResponse> {
  const { data } = await api.post('/generations', req);
  return data;
}

export async function getGeneration(runId: string): Promise<GenerationDetail> {
  const { data } = await api.get(`/generations/${runId}`);
  return data;
}

export async function continueGeneration(
  runId: string,
  content: string,
): Promise<GenerationResponse> {
  const { data } = await api.post(`/generations/${runId}/continue`, {
    content,
  });
  return data;
}

export async function createVariations(
  runId: string,
): Promise<GenerationResponse> {
  const { data } = await api.post(`/generations/${runId}/variations`);
  return data;
}

export async function generateImage(
  runId: string,
  req: ImageGenerateRequest,
): Promise<ImageResult> {
  const { data } = await api.post(`/generations/${runId}/image`, req);
  return data;
}

export async function composeCard(
  runId: string,
  req: ComposeRequest,
): Promise<ComposeCardResult> {
  const { data } = await api.post(`/generations/${runId}/compose`, req);
  return data;
}
