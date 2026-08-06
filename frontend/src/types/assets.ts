export interface AssetItem {
  id: string;
  name: string;
  asset_type: string;
  size_bytes: number;
  usage_count: number;
  indexed: boolean;
}

export interface AssetIndexResult {
  indexed: boolean;
  chunks: number;
}
