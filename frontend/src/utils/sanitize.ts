import DOMPurify from 'dompurify';

/**
 * Sanitize HTML before rendering. Security decision: only a whitelist of
 * text-formatting/layout tags and safe attributes survives — scripts,
 * iframes and inline event handlers are stripped by DOMPurify.
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [
      'b',
      'i',
      'em',
      'strong',
      'a',
      'p',
      'br',
      'ul',
      'ol',
      'li',
      'code',
      'pre',
      'blockquote',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'hr',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'span',
      'div',
      'img',
    ],
    ALLOWED_ATTR: [
      'href',
      'target',
      'rel',
      'src',
      'alt',
      'class',
      'width',
      'height',
    ],
  });
}
