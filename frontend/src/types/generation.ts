/** 请求体 camelCase（后端 pydantic to_camel alias） */

export interface GenerationCreateRequest {
  contentType?: string;
  generationMode?: string;
  topic: string;
  additionalRequirements?: string;
  assetIds?: string[];
  keyId?: string;
  model?: string;
  templateId?: string;
}

export interface ImageGenerateRequest {
  prompt: string;
  provider: string;
  keyId?: string;
}

export interface ComposeRequest {
  templateId: string;
  title?: string;
  summary?: string;
}

/** 响应体 snake_case（后端 model 默认序列化） */

export interface GenerationResponse {
  run_id: string;
  session_id: string | null;
  status: string;
}

export interface GenerationListItem {
  run_id: string;
  session_id: string | null;
  topic: string | null;
  content_type: string | null;
  generation_mode: string | null;
  status: string | null;
  result: Record<string, unknown>;
  created_at: string | null;
}

export interface GenerationDetail {
  id: string;
  session_id: string | null;
  topic: string;
  content_type: string;
  generation_mode: string;
  status: string;
  result: Record<string, unknown>;
  created_at: string | null;
}

export interface ImageResult {
  attachment_id: string;
  filename: string;
}

export interface ComposeTemplate {
  id: string;
  name: string;
  layout: Record<string, unknown>;
  is_default: boolean;
}

export interface ComposeCardResult {
  template: ComposeTemplate;
  fields: {
    title: string;
    summary: string;
    image_attachment_ids: string[];
  };
}
