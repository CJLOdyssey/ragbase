export interface AssetItem {
  id: string;
  name: string;
  assetType: string;
  sizeBytes: number;
  usageCount: number;
  indexed: boolean;
  knowledgeBaseId?: string | null;
  source?: string;
  sourceRef?: string | null;
}

export interface AssetIndexResult {
  indexed: boolean;
  chunks: number;
}
