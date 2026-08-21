import { Download, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  url: string;
  fileName: string;
  isImage: boolean;
  isText: boolean;
  text: string | null;
  loading: boolean;
  failed: boolean;
  imgFailed: boolean;
  truncated?: boolean;
  onImgError: () => void;
}

function ImageBlock({
  url,
  fileName,
  imgFailed,
  onImgError,
}: Pick<Props, 'url' | 'fileName' | 'imgFailed' | 'onImgError'>) {
  const { t } = useTranslation();
  if (imgFailed) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-[var(--color-danger)] mb-4">
          {t('attachment.imageLoadFailed')}
        </p>
        <a
          href={url}
          download={fileName}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
        >
          <Download size={14} />
          {t('attachment.download')}
        </a>
      </div>
    );
  }
  return (
    <img
      src={url}
      alt={fileName}
      className="mx-auto max-w-full max-h-[70vh] object-contain rounded-lg"
      onError={onImgError}
    />
  );
}

function TextBlock({
  url,
  fileName,
  text,
  loading,
  failed,
  truncated,
}: Pick<
  Props,
  'url' | 'fileName' | 'text' | 'loading' | 'failed' | 'truncated'
>) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-[var(--color-text-muted)] text-sm">
        <Loader2 size={18} className="animate-spin" />
        {t('common.loading')}
      </div>
    );
  }
  if (failed) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-[var(--color-danger)] mb-4">
          {t('attachment.previewLoadFailed')}
        </p>
        <a
          href={url}
          download={fileName}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
        >
          <Download size={14} />
          {t('attachment.download')}
        </a>
      </div>
    );
  }
  if (text === null) return null;
  if (text === '') {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-[var(--color-text-muted)] mb-4">
          {t('attachment.emptyPreview', {
            defaultValue: '文件为空或无可预览内容',
          })}
        </p>
        <a
          href={url}
          download={fileName}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
        >
          <Download size={14} />
          {t('attachment.download')}
        </a>
      </div>
    );
  }
  const previewTruncated =
    text.length > 64 * 1024
      ? `${text.slice(0, 64 * 1024)}\n\n${t('attachment.truncated')}`
      : text;
  const showNote = Boolean(truncated) || text.length > 64 * 1024;
  return (
    <div>
      <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--color-text-primary)]">
        {previewTruncated}
      </pre>
      {showNote && (
        <div className="text-[11px] text-[var(--color-text-tertiary)] mt-2">
          {t('attachment.truncated')}
        </div>
      )}
    </div>
  );
}

function UnsupportedBlock({ url, fileName }: Pick<Props, 'url' | 'fileName'>) {
  const { t } = useTranslation();
  return (
    <div className="py-8 text-center">
      <p className="text-sm text-[var(--color-text-muted)] mb-4">
        {t('attachment.unsupportedType')}
      </p>
      <a
        href={url}
        download={fileName}
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
      >
        <Download size={14} />
        {t('attachment.download')}
      </a>
    </div>
  );
}

export default function FilePreview(props: Props) {
  const {
    url,
    fileName,
    isImage,
    isText,
    text,
    loading,
    failed,
    imgFailed,
    truncated,
    onImgError,
  } = props;
  return (
    <div className="flex-1 overflow-auto">
      {isImage && (
        <ImageBlock
          url={url}
          fileName={fileName}
          imgFailed={imgFailed}
          onImgError={onImgError}
        />
      )}
      {isText && (
        <TextBlock
          url={url}
          fileName={fileName}
          text={text}
          loading={loading}
          failed={failed}
          truncated={truncated}
        />
      )}
      {!isImage && !isText && (
        <UnsupportedBlock url={url} fileName={fileName} />
      )}
    </div>
  );
}
