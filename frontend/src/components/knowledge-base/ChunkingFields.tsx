import { Form, InputNumber } from 'antd';
import { useTranslation } from 'react-i18next';

/**
 * Chunking-parameter fields bound to the enclosing antd Form context.
 * Kept separate from KbNewModal to hold the cross-field overlap<size rule.
 */
export default function ChunkingFields() {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 gap-3">
      <Form.Item
        name="chunkSize"
        label={t('kb.chunkSize')}
        extra={t('kb.chunkSizeHint')}
        rules={[{ required: true, message: t('kb.chunkSizeRequired') }]}
      >
        <InputNumber min={50} max={2000} step={50} className="!w-full" />
      </Form.Item>
      <Form.Item
        name="overlap"
        label={t('kb.overlap')}
        extra={t('kb.overlapHint')}
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
      >
        <InputNumber min={0} max={500} step={10} className="!w-full" />
      </Form.Item>
    </div>
  );
}
