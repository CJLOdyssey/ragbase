import { useEffect } from 'react';
import { Form, Input, Modal, Select } from 'antd';
import { useTranslation } from 'react-i18next';
import type { ModelInfo } from '../../api/client/models';

export interface KbNewModalProps {
  open: boolean;
  mode: 'create' | 'edit';
  initialName: string;
  initialDescription: string;
  models: ModelInfo[];
  saving: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => void;
}

const STRATEGIES = [
  { value: '相似度检索', key: 'strategySimilarity' },
  { value: '混合检索', key: 'strategyHybrid' },
  { value: 'MMR 多样性', key: 'strategyMmr' },
];

export default function KbNewModal({
  open,
  mode,
  initialName,
  initialDescription,
  models,
  saving,
  onClose,
  onSave,
}: KbNewModalProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        name: initialName,
        description: initialDescription,
        embedModel: models[0]?.id ?? undefined,
        strategy: STRATEGIES[0].value,
      });
    }
  }, [open, initialName, initialDescription, models, form]);

  const handleOk = async () => {
    const values = await form.validateFields();
    if (!values.name?.trim()) return;
    onSave(values.name.trim(), values.description?.trim() ?? '');
  };

  const isCreate = mode === 'create';

  return (
    <Modal
      title={isCreate ? t('kb.createTitle') : t('kb.editTitle')}
      open={open}
      onCancel={onClose}
      okText={t('confirm.confirm')}
      cancelText={t('confirm.cancel')}
      confirmLoading={saving}
      onOk={handleOk}
      okButtonProps={{
        className:
          '!bg-[var(--color-accent)] !border-none !text-[var(--color-text-on-accent)]',
      }}
      cancelButtonProps={{
        className:
          '!bg-[var(--color-surface-raised)] !border-none !text-[var(--color-text-secondary)]',
      }}
      width={480}
    >
      <Form form={form} layout="vertical" requiredMark={false} className="pt-2">
        <Form.Item
          name="name"
          label={t('kb.name')}
          rules={[{ required: true, message: t('kb.nameRequired') }]}
        >
          <Input
            placeholder={t('kb.namePlaceholder')}
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !text-[var(--color-text-primary)]"
          />
        </Form.Item>

        <Form.Item name="description" label={t('kb.description')}>
          <Input.TextArea
            rows={3}
            placeholder={t('kb.descriptionPlaceholder')}
            className="!bg-[var(--color-surface)] !border-[var(--color-border)] !text-[var(--color-text-primary)] resize-none"
          />
        </Form.Item>

        {isCreate && (
          <>
            <Form.Item name="embedModel" label={t('kb.embedModel')}>
              <Select
                showSearch={false}
                placeholder={t('kb.embedModelPlaceholder')}
                options={models.map((m) => ({
                  value: m.id,
                  label: m.label || m.id,
                }))}
              />
            </Form.Item>

            <Form.Item name="strategy" label={t('kb.strategy')}>
              <Select
                showSearch={false}
                options={STRATEGIES.map((s) => ({
                  value: s.value,
                  label: t(`kb.${s.key}`),
                }))}
              />
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
}
