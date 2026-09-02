import DOMPurify from 'dompurify';

// 新开标签页的链接强制 noopener+noreferrer：白名单允许 target/_blank，
// 若不强制 rel，LLM/用户内容生成的 <a target="_blank"> 存在 tabnabbing 隐患。
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    const target = node.getAttribute('target');
    if (target && target.toLowerCase() === '_blank') {
      node.setAttribute('rel', 'noopener noreferrer');
    }
  }
});

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
