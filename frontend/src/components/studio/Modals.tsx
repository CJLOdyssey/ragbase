import ApiManagementModal from '../settings/ApiManagementModal';
import SettingsModal from '../settings/SettingsModal';

interface ModalsProps {
  isSettingsOpen: boolean;
  isApiOpen: boolean;
  onCloseSettings: () => void;
  onCloseApi: () => void;
}

export default function Modals({
  isSettingsOpen,
  isApiOpen,
  onCloseSettings,
  onCloseApi,
}: ModalsProps) {
  return (
    <>
      {isSettingsOpen && <SettingsModal onClose={onCloseSettings} />}
      {isApiOpen && <ApiManagementModal onClose={onCloseApi} />}
    </>
  );
}
