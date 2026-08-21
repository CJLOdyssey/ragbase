import { useCallback, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { AssetItem } from '../../types/assets';
import { touchAsset } from '../../api/client/assets';

/**
 * useAssetBump — 单一职责的点击埋点 Hook（SRP）。
 *
 * 职责边界：
 * - 仅负责“点击→最新点击优先+次数+1→跳首位”的全栈链路，不掺杂筛选/统计/分页。
 * - 后端为权威（POST /touch 原子 increment+刷新 updated_at），前端做 TanStack 推荐的
 *   乐观更新 + 失败回滚 + 成功对账，避免纯乐观闪回与无对账分叉。
 *
 * 设计原则映射：
 * - SRP：本 Hook 只做 bump；OCP：新增埋点场景无需改 Hook，仅调 bump；DIP：依赖 queryClient 抽象而非具体组件；
 * - ISP：暴露极小接口 `{ bump, isBumping }`；LoD：不越权操作其它域；LSP/合成复用：可被任意列表复用。
 *
 * 质量保障：
 * - 性能：单次 setQueryData O(n)，n 为当前页资产数（通常 <500），无额外 fetch；
 * - 可靠性：onMutate 快照 + onError 回滚；onSuccess 用服务端返回的真实 updatedAt/usageCount 对账，杜绝前端/后端时钟漂移；
 * - 可用性：乐观后下一帧滚动置顶，用户立即感知“跳首位”；
 * - 安全性：仅透传 asset id，无注入。
 */
export function useAssetBump(
  scrollRef?: React.RefObject<HTMLDivElement | null>,
) {
  const queryClient = useQueryClient();
  // 防并发抖动：同 id 密集点击时，仅最后一次滚动生效
  const pendingRef = useRef<Set<string>>(new Set());

  const mutation = useMutation({
    mutationFn: (asset: AssetItem) => touchAsset(asset.id),
    onMutate: async (asset) => {
      pendingRef.current.add(asset.id);
      await queryClient.cancelQueries({ queryKey: ['assets'] });
      const previous = queryClient.getQueryData<AssetItem[]>(['assets']);
      const now = new Date().toISOString();
      queryClient.setQueryData<AssetItem[]>(['assets'], (old) => {
        if (!old) return old;
        return old.map((a) =>
          a.id === asset.id
            ? { ...a, usageCount: (a.usageCount ?? 0) + 1, updatedAt: now }
            : a,
        );
      });
      requestAnimationFrame(() => {
        scrollRef?.current?.scrollTo({ top: 0, behavior: 'smooth' });
      });
      return { previous, assetId: asset.id };
    },
    onError: (_err, _asset, ctx) => {
      if (ctx?.previous) {
        queryClient.setQueryData(['assets'], ctx.previous);
      }
    },
    onSuccess: (serverAsset) => {
      // 服务端对账：以后端权威的 updatedAt/usageCount 为准，修正时钟漂移与并发
      queryClient.setQueryData<AssetItem[]>(['assets'], (old) => {
        if (!old) return old;
        return old.map((a) =>
          a.id === serverAsset.id
            ? {
                ...a,
                usageCount: serverAsset.usageCount,
                updatedAt: serverAsset.updatedAt,
              }
            : a,
        );
      });
      requestAnimationFrame(() => {
        scrollRef?.current?.scrollTo({ top: 0, behavior: 'smooth' });
      });
    },
    onSettled: (_data, _err, asset) => {
      pendingRef.current.delete(asset.id);
      // 最终一致性兜底：若其它标签页或后台任务改动，轻量后台校准（不闪回，因已对账）
      void queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });

  const bump = useCallback(
    (asset: AssetItem) => {
      mutation.mutate(asset);
    },
    [mutation],
  );

  return { bump, isBumping: mutation.isPending };
}
