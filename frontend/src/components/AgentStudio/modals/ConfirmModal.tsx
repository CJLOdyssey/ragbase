import ConfirmDialog from '@/components/shared/ConfirmDialog';
import type { ReactNode } from 'react';

interface Props {
  title: string | ReactNode;
  message: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export default function ConfirmModal(props: Props) {
  return <ConfirmDialog {...props} />;
}
