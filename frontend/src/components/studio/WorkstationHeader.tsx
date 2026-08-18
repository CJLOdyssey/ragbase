import { Moon, PanelLeft, Sun } from 'lucide-react';

interface WorkstationHeaderProps {
  isSidebarOpen: boolean;
  isDarkMode: boolean;
  onToggleSidebar: () => void;
  onToggleTheme: () => void;
}

export default function WorkstationHeader({
  isSidebarOpen,
  isDarkMode,
  onToggleSidebar,
  onToggleTheme,
}: WorkstationHeaderProps) {
  return (
    <header className="h-14 flex items-center justify-between px-4 flex-shrink-0 z-40 bg-[var(--color-surface)]">
      <div className="flex items-center gap-3">
        {!isSidebarOpen && (
          <button
            type="button"
            className="flex items-center justify-center w-8 h-8 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
            onClick={onToggleSidebar}
            aria-label="Expand sidebar"
          >
            <PanelLeft size={18} />
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="flex items-center justify-center w-8 h-8 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
          onClick={onToggleTheme}
          aria-label="Toggle dark mode"
        >
          {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
