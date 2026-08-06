/**
 * Shared types for the input component system.
 *
 * All input-related components and hooks depend on this single file
 * instead of importing from each other — zero circular dependencies.
 */

// ── Model ──

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  status?: 'deprecated' | 'sunset';
}

// ── Command ──

export interface CommandOption {
  id: string;
  name: string;
  description?: string;
  source?: 'local' | 'agent';
}

// ── File / Attachment ──

export interface AttachedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  file?: File;
}

export interface FileRejection {
  file: File;
  reason: 'size_exceeded' | 'type_denied';
}
