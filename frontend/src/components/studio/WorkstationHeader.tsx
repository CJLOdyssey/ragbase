import { Moon, Sun } from 'lucide-react';

interface WorkstationHeaderProps {
  isDarkMode: boolean;
  onToggleTheme: () => void;
}

export default function WorkstationHeader({
  isDarkMode,
  onToggleTheme,
}: WorkstationHeaderProps) {
  return (
    <header className="h-14 flex items-center justify-end px-4 flex-shrink-0 z-40 bg-[var(--color-surface)]">
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
