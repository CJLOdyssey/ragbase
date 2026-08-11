import { useEffect, useState } from 'react';
import type * as React from 'react';
import { listPrompts } from '../../../api/client/prompts';

export interface PickerItem {
  id: string;
  name: string;
  description: string;
  source?: string;
  is_builtin?: boolean;
}

export interface PickerDeps {
  setSystemPrompt: React.Dispatch<React.SetStateAction<string>>;
  setOutputConstraints: React.Dispatch<React.SetStateAction<string>>;
  addTool: (item: PickerItem) => void;
  addMcp: (item: PickerItem) => void;
  addSkill: (item: PickerItem) => void;
}

export function usePickerState(deps: PickerDeps) {
  const { setSystemPrompt, setOutputConstraints, addTool, addMcp, addSkill } =
    deps;
  const [pickerTab, setPickerTab] = useState<string | null>(null);
  const [pickerItems, setPickerItems] = useState<Record<string, PickerItem[]>>(
    {},
  );

  useEffect(() => {
    let cancelled = false;
    listPrompts()
      .then((items) => {
        if (cancelled) return;
        const systemItems = items
          .filter((p) => p.category === 'system')
          .map(
            (p) =>
              ({
                id: p.id,
                name: p.name,
                description:
                  p.content.length > 120
                    ? p.content.slice(0, 120) + '…'
                    : p.content,
                source: '提示词管理',
              }) as PickerItem,
          );
        const outputItems = items
          .filter((p) => p.category === 'output')
          .map(
            (o) =>
              ({
                id: o.id,
                name: o.name,
                description: o.content,
                source: '输出管理',
              }) as PickerItem,
          );
        setPickerItems((prev) => ({
          ...prev,
          system: systemItems,
          output: outputItems,
        }));
      })
      .catch(() => {});
    // ponytail: tools/mcp/skills 无对应 API（主工作台已裁剪），留空等主窗口接入
    return () => {
      cancelled = true;
    };
  }, []);

  function handlePickerSelect(tab: string, item: PickerItem) {
    switch (tab) {
      case 'system':
        setSystemPrompt(
          (prev) => prev + (prev ? '\n\n' : '') + item.description,
        );
        break;
      case 'output':
        setOutputConstraints(
          (prev) => prev + (prev ? '\n' : '') + item.description,
        );
        break;
      case 'tools':
        addTool(item);
        break;
      case 'mcp':
        addMcp(item);
        break;
      case 'skills':
        addSkill(item);
        break;
    }
    setPickerTab(null);
  }

  return {
    pickerTab,
    pickerItems,
    handlePickerSelect,
    setPickerTab,
    setPickerItems,
  };
}
