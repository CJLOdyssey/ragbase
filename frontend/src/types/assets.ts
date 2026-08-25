export interface AssetItem {
  id: string;
  name: string;
  assetType: string;
  sizeBytes: number;
  usageCount: number;
  indexed: boolean;
  /** 最近一次索引失败原因（后端持久化终态）；null/缺省 = 无失败 */
  indexError?: string | null;
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
