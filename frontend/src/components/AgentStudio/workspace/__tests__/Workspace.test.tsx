import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

const mockGetAgentType = vi.fn().mockReturnValue('ui');
const mockGetWorkspaceTabs = vi.fn().mockReturnValue([
  { id: 'code', labelKey: 'workspace.code', icon: () => <span data-testid="icon-code">C</span> },
  { id: 'preview', labelKey: 'workspace.preview', icon: () => <span data-testid="icon-preview">P</span> },
  { id: 'frontend-code', labelKey: 'workspace.frontendCode', icon: () => <span data-testid="icon-fc">FC</span> },
  { id: 'frontend-test', labelKey: 'workspace.frontendTest', icon: () => <span data-testid="icon-ft">FT</span> },
]);

vi.mock('../../../../utils/workspaceConfig', () => ({
  getAgentType: (...args: unknown[]) => mockGetAgentType(...args),
  getWorkspaceTabs: (...args: unknown[]) => mockGetWorkspaceTabs(...args),
}));

vi.mock('lucide-react', () => ({
  Maximize2: () => <span data-testid="icon-maximize">Max</span>,
  PanelRightClose: () => <span data-testid="icon-collapse">Collapse</span>,
  FolderKanban: () => <span data-testid="icon-folder">Folder</span>,
  FileCode: () => <span data-testid="icon-filecode">FC</span>,
}));

import Workspace from '../Workspace';

const baseProps = {
  selectedAgentId: 'agent-1',
  activeTab: 'code' as const,
  setActiveTab: vi.fn(),
  isWorkspaceOpen: true,
  setIsWorkspaceOpen: vi.fn(),
  toggleWorkspaceFullscreen: vi.fn(),
  workspaceRef: { current: null },
};

describe('Workspace', { tags: ['integration'] }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when selectedAgentId is null', () => {
    const { container } = render(<Workspace {...baseProps} selectedAgentId={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null when isWorkspaceOpen is false', () => {
    const { container } = render(<Workspace {...baseProps} isWorkspaceOpen={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders workspace aside element', () => {
    const { container } = render(<Workspace {...baseProps} />);
    expect(container.querySelector('aside')).toBeInTheDocument();
  });

  it('renders tab buttons', () => {
    render(<Workspace {...baseProps} />);
    expect(screen.getByText('workspace.code')).toBeInTheDocument();
    expect(screen.getByText('workspace.preview')).toBeInTheDocument();
    expect(screen.getByText('workspace.frontendCode')).toBeInTheDocument();
    expect(screen.getByText('workspace.frontendTest')).toBeInTheDocument();
  });

  it('highlights active tab when selected', () => {
    render(<Workspace {...baseProps} activeTab="code" />);
    const codeBtn = screen.getByText('workspace.code').closest('button');
    const previewBtn = screen.getByText('workspace.preview').closest('button');
    expect(codeBtn?.className).toContain('bg-[var(--color-accent)]');
    expect(previewBtn?.className).not.toContain('bg-[var(--color-accent)]');
  });

  it('calls setActiveTab when tab clicked', () => {
    const setActiveTab = vi.fn();
    render(<Workspace {...baseProps} setActiveTab={setActiveTab} />);
    fireEvent.click(screen.getByText('workspace.preview'));
    expect(setActiveTab).toHaveBeenCalledWith('preview');
  });

  it('renders fullscreen button', () => {
    render(<Workspace {...baseProps} />);
    expect(screen.getByTitle('workspace.fullscreen')).toBeInTheDocument();
  });

  it('renders collapse button', () => {
    render(<Workspace {...baseProps} />);
    expect(screen.getByTitle('workspace.collapse')).toBeInTheDocument();
  });

  it('calls toggleWorkspaceFullscreen when fullscreen clicked', () => {
    const toggleWorkspaceFullscreen = vi.fn();
    render(<Workspace {...baseProps} toggleWorkspaceFullscreen={toggleWorkspaceFullscreen} />);
    fireEvent.click(screen.getByTitle('workspace.fullscreen'));
    expect(toggleWorkspaceFullscreen).toHaveBeenCalledOnce();
  });

  it('calls setIsWorkspaceOpen(false) when collapse clicked', () => {
    const setIsWorkspaceOpen = vi.fn();
    render(<Workspace {...baseProps} setIsWorkspaceOpen={setIsWorkspaceOpen} />);
    fireEvent.click(screen.getByTitle('workspace.collapse'));
    expect(setIsWorkspaceOpen).toHaveBeenCalledWith(false);
  });

  it('renders file explorer with empty tree', () => {
    render(<Workspace {...baseProps} />);
    expect(screen.getByText('workspace.fileExplorer')).toBeInTheDocument();
    expect(screen.getByText('workspace.emptyFiles')).toBeInTheDocument();
  });

  it('renders code editor content by default', () => {
    render(<Workspace {...baseProps} activeTab="code" />);
    expect(screen.getByText('workspace.committedJustNow')).toBeInTheDocument();
  });

  it('renders preview content for preview tab', () => {
    render(<Workspace {...baseProps} activeTab="preview" />);
    expect(screen.getByText('workspace.noPreview')).toBeInTheDocument();
  });

  it('renders test content for test tab', () => {
    render(<Workspace {...baseProps} activeTab="frontend-test" />);
    expect(screen.getByText('workspace.testRunner')).toBeInTheDocument();
    expect(screen.getByText('workspace.noTests')).toBeInTheDocument();
  });

  it('renders status bar', () => {
    render(<Workspace {...baseProps} />);
    expect(screen.getByText('workspace.noErrors')).toBeInTheDocument();
  });
});
