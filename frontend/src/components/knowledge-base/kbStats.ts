import type { AssetItem } from '../../types/assets';
import type { KnowledgeBase } from '../../api/client/knowledgeBases';

export interface KbStat {
  assetCount: number;
  indexedCount: number;
}

export const EMPTY_STAT: KbStat = { assetCount: 0, indexedCount: 0 };

/** Per-KB asset/indexed tallies computed from the full asset list. */
export function computePerKb(assets: AssetItem[]): Map<string, KbStat> {
  const map = new Map<string, KbStat>();
  for (const a of assets) {
    if (!a.knowledgeBaseId) continue;
    const cur = map.get(a.knowledgeBaseId) ?? { ...EMPTY_STAT };
    cur.assetCount += 1;
    if (a.indexed) cur.indexedCount += 1;
    map.set(a.knowledgeBaseId, cur);
  }
  return map;
}

/** Portfolio totals: backend asset_count wins when present (authoritative). */
export function computeTotals(
  kbs: KnowledgeBase[],
  perKb: Map<string, KbStat>,
): { totalAssets: number; indexedRate: number } {
  let total = 0;
  let indexed = 0;
  for (const kb of kbs) {
    const s = perKb.get(kb.id) ?? EMPTY_STAT;
    total += kb.assetCount ?? s.assetCount;
    indexed += s.indexedCount;
  }
  // indexed 来自前端 assets 列表、total 可能来自后端 kb.assetCount，
  // 两 query 刷新时机不同（upload 只失效 ['assets']）——混算可能瞬时 >100%，
  // 收敛到 100 并保底 0（口径说明：刷新后一致即回落真实值）。
  const rate = total > 0 ? Math.round((indexed / total) * 100) : 0;
  return {
    totalAssets: total,
    indexedRate: Math.min(100, Math.max(0, rate)),
  };
}
