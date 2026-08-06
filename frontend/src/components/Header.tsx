import { PanelLeft } from 'lucide-react';

interface Props {
  onToggleSidebar: () => void;
}

export default function Header({ onToggleSidebar }: Props) {
  return (
    <header className="agentstudio-header">
      <div className="agentstudio-header-left">
        <button
          className="agentstudio-header-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          <PanelLeft size={20} />
        </button>
      </div>
    </header>
  );
}
