import type { ReactNode } from 'react';
import ConfirmDialog from '@/components/shared/ConfirmDialog';

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
