import { Moon, PanelLeft, Sun } from 'lucide-react';

interface WorkstationHeaderProps {
  isDarkMode: boolean;
  onToggleTheme: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export default function WorkstationHeader({
  isDarkMode,
  onToggleTheme,
  isSidebarOpen,
  onToggleSidebar,
}: WorkstationHeaderProps) {
  return (
    <header className="h-14 flex items-center px-4 flex-shrink-0 z-40 bg-[var(--color-surface)]">
      {!isSidebarOpen && (
        <button
          type="button"
          className="flex items-center justify-center w-9 h-9 bg-transparent border-none rounded-lg text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] mr-3"
          onClick={onToggleSidebar}
          aria-label="Open sidebar"
        >
          <PanelLeft size={20} />
        </button>
      )}
      <div className="flex-1" />
      <button
        type="button"
        className="flex items-center justify-center w-8 h-8 bg-transparent border-none rounded-md text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
        onClick={onToggleTheme}
        aria-label="Toggle dark mode"
      >
        {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
}
