import { describe, it, expect } from 'vitest';
import { sanitizeHtml } from '../sanitize';

describe('sanitizeHtml', { tags: ['unit'] }, () => {
  it('passes through safe HTML', () => {
    const result = sanitizeHtml('<b>hello</b>');
    expect(result).toContain('hello');
  });

  it('strips script tags', () => {
    const result = sanitizeHtml('<script>alert("xss")</script>hello');
    expect(result).not.toContain('script');
    expect(result).toContain('hello');
  });

  it('keeps allowed tags', () => {
    const result = sanitizeHtml('<b>bold</b> <i>italic</i> <p>paragraph</p>');
    expect(result).toContain('<b>');
    expect(result).toContain('<i>');
    expect(result).toContain('<p>');
  });

  it('strips event handlers', () => {
    const result = sanitizeHtml('<div onclick="alert(1)">safe</div>');
    expect(result).not.toContain('onclick');
    expect(result).toContain('safe');
  });

  it('handles empty string', () => {
    const result = sanitizeHtml('');
    expect(result).toBe('');
  });

  it('keeps allowed attributes', () => {
    const result = sanitizeHtml('<a href="https://example.com" target="_blank">link</a>');
    expect(result).toContain('href');
    expect(result).toContain('target');
  });
});
