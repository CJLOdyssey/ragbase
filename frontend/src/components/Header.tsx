import { PanelLeft } from 'lucide-react';

interface Props {
  onToggleSidebar: () => void;
}

export default function Header({ onToggleSidebar }: Props) {
  return (
    <header className="ragbase-header">
      <div className="ragbase-header-left">
        <button
          className="ragbase-header-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          <PanelLeft size={20} />
        </button>
      </div>
    </header>
  );
}
