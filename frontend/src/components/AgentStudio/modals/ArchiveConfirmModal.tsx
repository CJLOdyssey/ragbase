import { Archive } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ConfirmDialog from '@/components/shared/ConfirmDialog';

interface Props {
  kindName: string;
  name: string;
  onArchive: () => void;
  onCancel: () => void;
}

export default function ArchiveConfirmModal({ kindName, name, onArchive, onCancel }: Props) {
  const { t } = useTranslation();

  return (
    <ConfirmDialog
      title={
        <div className="flex items-center gap-2">
          <Archive size={16} />
          {t('workstation.archiveConfirmTitle')}
        </div>
      }
      message={t('workstation.archiveConfirmDesc', { tool: kindName, name })}
      confirmLabel={t('workstation.archiveBtn')}
      cancelLabel={t('workstation.cancel')}
      icon={<Archive size={24} className="text-[var(--color-accent)]" />}
      onConfirm={onArchive}
      onCancel={onCancel}
      width={400}
    />
  );
}
