import { Form, InputNumber } from 'antd';
import { useTranslation } from 'react-i18next';

/**
 * Chunking-parameter fields bound to the enclosing antd Form context.
 * Kept separate from KbNewModal to hold the cross-field overlap<size rule.
 */
export default function ChunkingFields() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1">
      <div className="grid grid-cols-2 gap-3">
        <Form.Item
          name="chunkSize"
          label={
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {t('kb.chunkSize')}
            </span>
          }
          rules={[{ required: true, message: t('kb.chunkSizeRequired') }]}
          className="!mb-0"
        >
          <InputNumber
            min={50}
            max={2000}
            step={50}
            className="!w-full !rounded-lg"
            parser={(value) => Number(value?.replace(/\D/g, '')) || 0}
          />
        </Form.Item>
        <Form.Item
          name="overlap"
          label={
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {t('kb.overlap')}
            </span>
          }
          dependencies={['chunkSize']}
          rules={[
            { required: true, message: t('kb.overlapRequired') },
            ({ getFieldValue }) => ({
              validator: (_, value) => {
                const size = getFieldValue('chunkSize');
                if (
                  value == null ||
                  size == null ||
                  (value >= 0 && value < size)
                ) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error(t('kb.overlapLessThanSize')));
              },
            }),
          ]}
          className="!mb-0"
        >
          <InputNumber
            min={0}
            max={500}
            step={10}
            className="!w-full !rounded-lg"
            parser={(value) => Number(value?.replace(/\D/g, '')) || 0}
          />
        </Form.Item>
      </div>
      <p className="m-0 text-[11px] text-[var(--color-text-muted)] leading-tight">
        {t('kb.chunkSizeHint')}；{t('kb.overlapHint')}
      </p>
    </div>
  );
}
