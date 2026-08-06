#!/usr/bin/env python3
"""Replace wsta-* CSS classes with Tailwind v4 utilities - comprehensive."""
import re

FILES = [
    "src/components/agentstudio/workstation/tool/ToolManagement.tsx",
    "src/components/agentstudio/workstation/tool/ToolFormModal.tsx",
    "src/components/agentstudio/workstation/mcp/MCPManagement.tsx",
    "src/components/agentstudio/workstation/mcp/MCPFormModal.tsx",
    "src/components/agentstudio/workstation/skill/SkillManagement.tsx",
    "src/components/agentstudio/workstation/skill/SkillFormModal.tsx",
    "src/components/agentstudio/workstation/team/TeamFormModal.tsx",
    "src/components/agentstudio/workstation/output/OutputFormModal.tsx",
    "src/components/agentstudio/workstation/output/OutputConstraintManagement.tsx",
    "src/components/agentstudio/workstation/prompt/PromptFormModal.tsx",
    "src/components/agentstudio/workstation/shared/DeleteConfirmModal.tsx",
    "src/components/agentstudio/workstation/shared/BatchDeleteModal.tsx",
    "src/components/agentstudio/workstation/shared/ResourcePickerModal.tsx",
    "src/components/agentstudio/workstation/shared/VersionHistoryModal.tsx",
    "src/components/agentstudio/workstation/shared/ErrorBoundary.tsx",
    "src/components/agentstudio/workstation/logs/LogAudit.tsx",
    "src/components/agentstudio/workstation/settings/SystemSettings.tsx",
    "src/components/agentstudio/workstation/monitor/MonitorCenter.tsx",
    "src/components/agentstudio/workstation/shared/searchable-select.tsx",
]

REPLACEMENTS = [
    # ===== VERSION HISTORY =====
    (r'\bwsta-version-compare-toolbar\b', 'flex items-center gap-2'),
    (r'\bwsta-version-compare-hint\b', 'text-sm text-muted-foreground mb-3'),
    (r'\bwsta-version-compare-selected\b', 'text-primary font-medium'),
    (r'\bwsta-version-diff-container\b', 'grid grid-cols-2 gap-0 mt-4 border border-border rounded-md overflow-hidden'),
    (r'\bwsta-version-diff\b', 'flex gap-4'),
    (r'\bwsta-version-diff-pane\b', 'flex-1 min-w-0'),
    (r'\bwsta-diff-pane\b', 'flex-1 min-w-0'),
    (r'\bwsta-diff-header\b', 'text-sm font-medium text-muted-foreground mb-2'),
    (r'\bwsta-diff-line\b', 'text-xs font-mono py-0.5 px-2 whitespace-pre-wrap break-all'),
    (r'\bwsta-diff-added\b', 'bg-green-500/10 text-green-600 dark:text-green-400'),
    (r'\bwsta-diff-removed\b', 'bg-red-500/10 text-red-600 dark:text-red-400'),
    (r'\bwsta-diff-unchanged\b', 'text-muted-foreground'),
    (r'\bwsta-diff-controls\b', 'flex items-center gap-2'),
    (r'\bwsta-version-item-selectable\b', 'cursor-pointer transition-colors hover:border-primary'),
    (r'\bwsta-version-item-selected\b', 'border-primary! bg-primary/5!'),
    (r'\bwsta-version-item-check\b', 'shrink-0 text-primary ml-2'),
    (r'\bwsta-version-item-preview\b', 'text-xs text-muted-foreground font-mono truncate max-w-[200px]'),
    (r'\bwsta-version-item-content\b', 'flex-1 min-w-0'),
    (r'\bwsta-version-item-actions\b', 'shrink-0 flex items-center gap-1'),
    (r'\bwsta-version-item\b', 'flex items-center gap-3 p-3 rounded-md border border-border bg-card hover:bg-accent/50 transition-colors cursor-pointer'),
    (r'\bwsta-version-content\b', 'mt-2 text-xs text-muted-foreground font-mono leading-relaxed whitespace-pre-wrap break-words'),
    (r'\bwsta-version-list\b', 'space-y-2'),
    (r'\bwsta-version-header\b', 'flex items-center justify-between px-3 py-2 border-b border-border'),
    (r'\bwsta-version-modal\b', 'flex flex-col h-[500px]'),
    (r'\bwsta-version-tag\b', 'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary/15 text-primary'),
    (r'\bwsta-version-date\b', 'text-xs text-muted-foreground'),
    (r'\bwsta-version-author\b', 'text-xs text-muted-foreground'),
    (r'\bwsta-version-changes\b', 'text-sm text-muted-foreground mt-0'),
    (r'\bwsta-version-check\b', 'ml-auto text-primary font-bold text-sm'),
    (r'\bwsta-code-preview\b', 'text-xs text-muted-foreground font-mono truncate max-w-[200px]'),

    # ===== LOG AUDIT =====
    (r'\bwsta-log-detail-card\b', 'rounded-lg border bg-card p-4 shadow-sm'),
    (r'\bwsta-log-level-active\b', 'bg-accent text-accent-foreground'),
    (r'\bwsta-log-level-badge\b', 'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium'),
    (r'\bwsta-log-module-badge\b', 'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-muted'),
    (r'\bwsta-log-module\b', 'min-w-[80px]'),
    (r'\bwsta-log-pagination\b', 'flex items-center justify-between pt-3 border-t border-border'),
    (r'\bwsta-log-table-wrap\b', 'flex-1 min-h-0 overflow-y-auto'),
    (r'\bwsta-log-level\b', 'inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium cursor-pointer transition-colors'),
    (r'\bwsta-log-details\b', 'text-sm text-muted-foreground'),
    (r'\bwsta-logs-toolbar-right\b', 'flex items-center gap-2'),
    (r'\bwsta-logs-filters\b', 'flex items-center gap-1'),
    (r'\bwsta-logs-toolbar\b', 'flex items-center justify-between gap-3 mb-3 flex-wrap'),
    (r'\bwsta-logs\b', 'flex flex-col p-4'),

    # ===== SETTINGS =====
    (r'\bwsta-settings-field-hint\b', 'text-xs text-muted-foreground mt-0.5'),
    (r'\bwsta-settings-field-control\b', 'min-w-[200px] flex items-center gap-2 shrink-0'),
    (r'\bwsta-settings-field-label\b', 'text-sm font-medium text-foreground'),
    (r'\bwsta-settings-field\b', 'flex items-center justify-between py-3 gap-4'),
    (r'\bwsta-settings-fields\b', 'px-4 py-2'),
    (r'\bwsta-settings-section-header\b', 'flex items-center gap-2 px-4 py-2.5 border-b border-border text-muted-foreground'),
    (r'\bwsta-settings-section\b', 'rounded-lg border bg-card mb-4 overflow-hidden'),
    (r'\bwsta-settings-sections\b', 'space-y-4'),
    (r'\bwsta-settings-toast\b', 'flex items-center gap-2 px-4 py-2.5 mb-4 bg-green-600 text-white text-sm font-medium rounded-lg'),
    (r'\bwsta-settings-title\b', 'flex items-center gap-2 text-base font-semibold text-foreground'),
    (r'\bwsta-settings-header\b', 'flex items-center justify-between mb-3'),
    (r'\bwsta-settings\b', 'flex flex-col p-4 max-w-[50rem]'),
    (r'\bwsta-settings-footer\b', 'flex justify-end pt-2'),

    # ===== TOGGLE =====
    (r'\bwsta-toggle-slider\b', 'absolute inset-0 bg-muted-foreground/30 rounded-full transition-colors peer-checked:bg-primary'),
    (r'\bwsta-toggle-wrap\b', 'relative inline-flex items-center cursor-pointer'),
    (r'\bwsta-toggle-track\b', 'w-9 h-5 rounded-full bg-muted transition-colors peer-checked:bg-primary'),
    (r'\bwsta-toggle-knob\b', 'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-background shadow transition-transform peer-checked:translate-x-4'),

    # ===== TAGS AND STATUS =====
    (r'\bwsta-tag-team\b', 'bg-amber-500/10 text-amber-600 dark:text-amber-400'),
    (r'\bwsta-tag-model\b', 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'),
    (r'\bwsta-tag-tool-custom\b', 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'),
    (r'\bwsta-tag-tool-builtin\b', 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'),
    (r'\bwsta-tag-method\b', 'bg-violet-500/10 text-violet-600 dark:text-violet-400'),
    (r'\bwsta-tag-var\b', 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 cursor-default'),
    (r'\bwsta-tag\b', 'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium tracking-wide'),
    (r'\bwsta-status-dot\b', 'inline-block w-[5px] h-[5px] rounded-full'),
    (r'\bwsta-status-running\b', 'text-green-600 [.wsta-status-dot]:bg-green-500'),
    (r'\bwsta-status-stopped\b', 'text-muted-foreground [.wsta-status-dot]:bg-muted-foreground'),
    (r'\bwsta-status-error\b', 'text-destructive [.wsta-status-dot]:bg-destructive'),
    (r'\bwsta-status-tag\b', 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium'),
    (r'\bwsta-status-active\b', 'bg-green-500/10 text-green-600 dark:text-green-400'),
    (r'\bwsta-status-inactive\b', 'bg-muted text-muted-foreground'),
    (r'\bwsta-status\b', 'inline-flex items-center gap-1.5 text-xs'),
    (r'\bwsta-version\b', 'text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono'),
    (r'\bwsta-agent-name\b', 'font-medium text-foreground'),

    # ===== CODE DISPLAY =====
    (r'\bwsta-code-indicator\b', 'inline-flex items-center gap-1 px-2 py-0.5 rounded bg-muted text-xs text-muted-foreground'),
    (r'\bwsta-code-block\b', 'rounded-md bg-muted overflow-hidden'),
    (r'\bwsta-code-header\b', 'flex items-center justify-between bg-muted/80 px-3 py-1.5 text-xs text-muted-foreground'),
    (r'\bwsta-code-content\b', 'p-3 text-sm font-mono overflow-x-auto'),
    (r'\bwsta-code\b', 'rounded bg-muted px-1 py-0.5 text-xs font-mono text-foreground'),

    # ===== RESOURCE PICKER =====
    (r'\bwsta-picker-empty\b', 'py-8 text-center text-sm text-muted-foreground'),
    (r'\bwsta-picker-item-check\b', 'shrink-0 text-primary'),
    (r'\bwsta-picker-item-info\b', 'flex-1 min-w-0'),
    (r'\bwsta-picker-item-label\b', 'text-sm font-medium text-foreground truncate'),
    (r'\bwsta-picker-item-secondary\b', 'text-xs text-muted-foreground truncate'),
    (r'\bwsta-picker-item\b', 'flex items-center justify-between gap-2 px-3 py-2.5 cursor-pointer hover:bg-accent transition-colors border-b border-border last:border-b-0'),
    (r'\bwsta-picker-search\b', 'flex items-center gap-2 px-3 py-2 border-b border-border'),
    (r'\bwsta-picker-list\b', 'max-h-[300px] overflow-y-auto p-2'),
    (r'\bwsta-picker-option\b', 'flex items-center justify-between gap-2 px-3 py-2 rounded-md cursor-pointer hover:bg-accent transition-colors'),
    (r'\bwsta-picker-option-selected\b', 'bg-accent/50 font-medium'),

    # ===== SEARCHABLE SELECT =====
    (r'\bwsta-searchable-select\b', 'relative'),
    (r'\bwsta-searchable-select-header\b', 'flex items-center min-h-[2.25rem] rounded-md border border-input bg-background px-3 py-1.5 cursor-pointer gap-1.5 flex-wrap'),
    (r'\bwsta-searchable-select-arrow\b', 'ml-auto shrink-0 text-muted-foreground'),
    (r'\bwsta-searchable-select-tags\b', 'flex flex-wrap gap-1 flex-1 min-w-0'),
    (r'\bwsta-searchable-select-tag\b', 'inline-flex items-center gap-0.5 px-2 py-0.5 rounded bg-muted text-xs'),
    (r'\bwsta-searchable-select-tag-remove\b', 'cursor-pointer text-muted-foreground hover:text-foreground ml-0.5'),
    (r'\bwsta-searchable-select-search\b', 'absolute z-50 mt-1 w-full rounded-md border border-border bg-popover shadow-lg max-h-60 overflow-y-auto'),

    # ===== ERROR / EMPTY STATE =====
    (r'\bwsta-error-state-msg\b', 'text-sm text-destructive'),
    (r'\bwsta-error-icon\b', 'h-8 w-8 text-destructive mb-2'),
    (r'\bwsta-error-state-title\b', 'text-base font-medium text-foreground'),
    (r'\bwsta-error-state-desc\b', 'text-sm text-muted-foreground'),
    (r'\bwsta-error-state-icon\b', 'h-12 w-12 text-muted-foreground opacity-40 mb-2'),
    (r'\bwsta-error-banner\b', 'flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive mb-3'),
    (r'\bwsta-error-state\b', 'flex flex-col items-center justify-center gap-3 py-16 px-4 text-center'),
    (r'\bwsta-empty-state-icon\b', 'h-10 w-10 text-muted-foreground opacity-50 mb-3'),
    (r'\bwsta-empty-state-title\b', 'text-lg font-semibold text-muted-foreground'),
    (r'\bwsta-empty-state-desc\b', 'text-sm text-muted-foreground mt-1 max-w-[320px]'),
    (r'\bwsta-empty-state\b', 'flex flex-col items-center justify-center gap-3 py-16 px-4 text-center text-muted-foreground flex-1'),
    (r'\bwsta-empty-cell\b', 'text-center py-12 px-4 text-muted-foreground'),

    # ===== MODAL =====
    (r'\bwsta-modal-lg\b', 'max-w-4xl'),
    (r'\bwsta-modal-md\b', 'max-w-lg'),
    (r'\bwsta-modal-sm\b', 'max-w-md'),
    (r'\bwsta-modal-title\b', 'text-lg font-semibold'),
    (r'\bwsta-modal-close\b', 'rounded-md p-1 hover:bg-accent transition-colors text-muted-foreground hover:text-foreground border-none bg-transparent cursor-pointer'),
    (r'\bwsta-modal-body\b', 'space-y-4'),
    (r'\bwsta-modal-header\b', 'mb-4 flex items-center justify-between'),
    (r'\bwsta-modal-footer\b', 'mt-6 flex items-center justify-end gap-2'),
    (r'\bwsta-modal\b', 'flex flex-col max-h-[85vh] overflow-hidden'),
    (r'\bwsta-modal-overlay\b', 'fixed inset-0 z-50 flex items-center justify-center bg-black/50'),
    (r'\bwsta-modal-content\b', 'relative w-full max-w-lg rounded-lg border bg-background p-6 shadow-lg'),
    (r'\bwsta-overlay\b', 'fixed inset-0 z-50 flex items-center justify-center bg-black/50'),

    # ===== FORM =====
    (r'\bwsta-form-section-title\b', 'flex items-center gap-2 text-sm font-semibold text-foreground mb-3'),
    (r'\bwsta-form-section\b', 'mt-5 pt-4 border-t border-border'),
    (r'\bwsta-form-error-item\b', 'text-sm text-destructive'),
    (r'\bwsta-form-errors\b', 'rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive'),
    (r'\bwsta-form-row\b', 'flex gap-4'),
    (r'\bwsta-form-grid\b', 'grid grid-cols-2 gap-4'),
    (r'\bwsta-form-group-full\b', 'col-span-2'),
    (r'\bwsta-form-group\b', 'space-y-2'),
    (r'\bwsta-form-label\b', 'text-sm font-medium text-foreground'),
    (r'\bwsta-form-input\b', 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none'),
    (r'\bwsta-form-textarea\b', 'flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none resize-y'),
    (r'\bwsta-label\b', 'text-xs font-medium text-muted-foreground'),
    (r'\bwsta-input\b', 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none'),
    (r'\bwsta-textarea\b', 'flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none resize-y'),
    (r'\bwsta-select\b', 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none cursor-pointer appearance-none'),
    (r'\bwsta-required\b', 'text-destructive ml-0.5'),
    (r'\bwsta-error\b', 'text-sm text-destructive'),
    (r'\bwsta-hint\b', 'text-xs text-muted-foreground'),

    # ===== RADIO GROUP =====
    (r'\bwsta-radio-group\b', 'flex items-center gap-6'),
    (r'\bwsta-radio\b', 'flex items-center gap-2 text-sm text-muted-foreground cursor-pointer'),

    # ===== HEADERS EDITOR =====
    (r'\bwsta-headers-editor\b', 'space-y-2 mt-2'),
    (r'\bwsta-header-row\b', 'flex items-center gap-2'),
    (r'\bwsta-header-key\b', 'flex-1 min-w-0'),
    (r'\bwsta-header-value\b', 'flex-1 min-w-0'),
    ('wsta-header-remove', 'shrink-0 flex items-center justify-center w-8 h-8 rounded-md border border-border bg-transparent text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 cursor-pointer transition-colors'),
    (r'\bwsta-header-add\b', 'text-sm text-primary hover:text-primary/80 hover:underline cursor-pointer border-none bg-transparent'),

    # ===== PROMPT / VARIABLES =====
    (r'\bwsta-char-count\b', 'text-xs text-muted-foreground text-right'),
    (r'\bwsta-token-estimate\b', 'text-muted-foreground'),
    (r'\bwsta-var-section\b', 'mt-2.5 flex flex-col gap-3'),
    (r'\bwsta-var-badge\b', 'text-xs font-medium text-amber-500'),
    (r'\bwsta-var-tags\b', 'flex flex-wrap gap-2'),
    (r'\bwsta-prompt-preview-label\b', 'text-[11px] text-muted-foreground mb-1 uppercase'),
    (r'\bwsta-prompt-preview\b', 'mt-2 px-3 py-2.5 rounded-md border bg-muted text-sm'),
    (r'\bwsta-resource-grid\b', 'grid grid-cols-2 gap-4'),

    # ===== SEARCH =====
    (r'\bwsta-search-clear\b', 'absolute right-2 text-muted-foreground hover:text-foreground border-none bg-transparent cursor-pointer p-0.5 rounded-sm'),
    (r'\bwsta-search-input\b', 'flex h-10 w-full max-w-xs rounded-md border border-input bg-background px-3 py-2 text-sm pl-9 outline-none'),
    (r'\bwsta-search-icon\b', 'absolute left-3 text-muted-foreground pointer-events-none'),
    (r'\bwsta-search-wrap\b', 'relative flex items-center'),

    # ===== FILTER =====
    (r'\bwsta-filter-select\b', 'flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none'),

    # ===== TABLE COLUMNS =====
    (r'\bwsta-th-check\b', 'w-10'),
    (r'\bwsta-td-check\b', 'w-10'),
    (r'\bwsta-th-actions\b', 'w-24 text-right'),
    (r'\bwsta-td-actions\b', 'w-24 text-right'),
    (r'\bwsta-col-actions\b', 'w-16 text-center'),
    (r'\bwsta-col-checkbox\b', 'w-10'),
    (r'\bwsta-col-expand\b', 'w-8'),
    (r'\bwsta-cell-name\b', 'font-medium text-foreground'),
    (r'\bwsta-cell-content\b', 'max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap text-muted-foreground'),
    (r'\bwsta-content-preview\b', 'text-xs text-muted-foreground line-clamp-2'),
    (r'\bwsta-tool-desc\b', 'max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap text-muted-foreground'),
    (r'\bwsta-tool-table\b', ''),
    (r'\bwsta-text-secondary\b', 'text-muted-foreground'),

    # ===== SORT =====
    (r'\bwsta-sort-icon-active\b', 'text-foreground'),
    (r'\bwsta-sort-icon-inactive\b', 'text-muted-foreground opacity-40'),
    (r'\bwsta-sortable\b', 'cursor-pointer select-none'),

    # ===== ROW =====
    (r'\bwsta-row-selected\b', 'bg-accent/50'),

    # ===== TABLE BASE =====
    (r'\bwsta-table-wrap\b', 'flex-1 min-h-0 overflow-y-auto'),
    (r'\bwsta-table\b', 'w-full table-fixed border-collapse text-sm'),

    # ===== TEXT / LINKS =====
    (r'\bwsta-name-link\b', 'text-primary hover:underline cursor-pointer'),
    (r'\bwsta-link\b', 'text-primary hover:underline cursor-pointer'),
    (r'\bwsta-prompt-name\b', 'text-foreground'),
    (r'\bwsta-text-muted\b', 'text-muted-foreground'),
    (r'\bwsta-no-data\b', 'flex items-center justify-center py-8 text-muted-foreground text-sm'),
    (r'\bwsta-confirm-text\b', 'text-sm text-muted-foreground leading-relaxed'),

    # ===== PAGE HEADER =====
    (r'\bwsta-page-header\b', 'flex items-center justify-between mb-4'),
    (r'\bwsta-page-title\b', 'text-lg font-semibold text-foreground'),
    (r'\bwsta-page-desc\b', 'text-sm text-muted-foreground'),
    (r'\bwsta-action-bar\b', 'flex items-center gap-2'),

    # ===== PANEL =====
    (r'\bwsta-panel\b', 'rounded-lg border bg-card text-card-foreground shadow-sm'),

    # ===== WRAPPERS =====
    (r'\bwsta-agent-mgmt\b', 'flex flex-col'),
    (r'\bwsta-flex-1\b', 'flex-1 min-w-0'),

    # ===== TOOLBAR =====
    (r'\bwsta-toolbar\b', 'flex items-center justify-between gap-3 py-2 px-2 shrink-0 border-b border-border mb-2'),
    (r'\bwsta-toolbar-left\b', 'flex items-center gap-3 flex-1'),
    (r'\bwsta-toolbar-right\b', 'flex items-center gap-3'),
    (r'\bwsta-create-btn\b', 'shrink-0'),
    (r'\bwsta-batch-bar\b', 'flex items-center gap-3 px-4 py-2 bg-accent/10 border border-accent/30 rounded-md'),

    # ===== PLUGINS =====
    (r'\bwsta-plugins-toggle\b', 'flex items-center gap-2 w-full text-left text-sm font-semibold text-muted-foreground bg-transparent border-none cursor-pointer p-1 hover:text-foreground'),
    (r'\bwsta-plugins-title\b', ''),
    (r'\bwsta-plugins-section\b', 'px-2 py-2 border-b border-border mb-2'),
    (r'\bwsta-plugins-grid\b', 'flex gap-3 flex-wrap'),
    (r'\bwsta-plugin-card\b', 'flex items-center gap-3 px-4 py-3 rounded-lg border bg-card min-w-[280px] transition-colors hover:border-accent hover:bg-accent/5'),
    (r'\bwsta-plugin-info\b', 'flex-1 min-w-0'),
    (r'\bwsta-plugin-btn\b', 'shrink-0'),

    # ===== ACTIONS =====
    (r'\bwsta-action-group\b', 'flex justify-center gap-0.5'),
    (r'\bwsta-action-btn\b', 'flex items-center justify-center w-7 h-7 rounded-md border-none bg-transparent text-muted-foreground cursor-pointer transition-colors hover:bg-accent hover:text-foreground'),
    (r'\bwsta-action-btn-danger\b', 'hover:bg-destructive/10 hover:text-destructive'),

    # ===== MONITOR =====
    (r'\bwsta-monitor-card-change\b', 'text-xs'),
    (r'\bwsta-monitor-card-value\b', 'text-2xl font-semibold tracking-tight text-foreground tabular-nums'),
    (r'\bwsta-monitor-card-label\b', 'text-sm font-medium text-muted-foreground'),
    (r'\bwsta-monitor-card-body\b', 'flex flex-col gap-0.5'),
    (r'\bwsta-monitor-card-icon\b', 'flex items-center justify-center w-11 h-11 rounded-lg shrink-0 bg-primary/10'),
    (r'\bwsta-monitor-card\b', 'flex items-center gap-3 p-3 rounded-lg border bg-card transition-colors hover:border-accent hover:shadow-sm'),
    (r'\bwsta-monitor-stats\b', 'grid grid-cols-2 gap-3 px-4 py-3'),
    (r'\bwsta-monitor-time\b', 'flex items-center gap-1.5 text-sm text-muted-foreground tabular-nums'),
    (r'\bwsta-monitor-title\b', 'flex items-center gap-2 text-base font-semibold text-foreground'),
    (r'\bwsta-monitor-header\b', 'flex items-center justify-between px-4 py-3 border-b border-border'),
    (r'\bwsta-monitor-section\b', 'mb-4'),
    (r'\bwsta-monitor-tables\b', 'space-y-4 px-4 py-3'),
    (r'\bwsta-monitor\b', 'flex flex-col'),

    # ===== PAGINATION / FOOTER =====
    (r'\bwsta-page-info\b', 'text-xs text-muted-foreground'),
    (r'\bwsta-page-num\b', 'text-sm text-muted-foreground font-medium'),
    (r'\bwsta-page-btns\b', 'flex items-center gap-1'),
    (r'\bwsta-footer-text\b', 'text-xs text-muted-foreground'),
    (r'\bwsta-footer\b', 'flex items-center justify-between px-4 py-2 border-t border-border shrink-0'),
    (r'\bwsta-pagination\b', 'flex items-center gap-1'),
    (r'\bwsta-page-btn\b', 'flex items-center justify-center min-w-[32px] h-8 px-2 rounded-md border border-border bg-transparent text-muted-foreground text-sm cursor-pointer transition-colors hover:bg-accent hover:text-foreground hover:border-accent disabled:opacity-40 disabled:cursor-not-allowed'),
]


def replace_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    if content == original:
        print(f"[SKIP] {filepath} — no changes")
        return False

    with open(filepath, 'w') as f:
        f.write(content)
    print(f"[DONE] {filepath}")
    return True


if __name__ == '__main__':
    count = 0
    for f in FILES:
        if replace_in_file(f):
            count += 1
    print(f"\nTotal files changed: {count}/{len(FILES)}")
