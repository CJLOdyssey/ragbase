export interface AssetItem {
  id: string;
  name: string;
  assetType: string;
  sizeBytes: number;
  usageCount: number;
  indexed: boolean;
  knowledgeBaseId?: string | null;
  tags?: string[];
  source?: string;
  sourceRef?: string | null;
  updatedAt?: string | null;
  chunkCount?: number | null;
}

export interface AssetIndexResult {
  indexed: boolean;
  chunks: number;
}
