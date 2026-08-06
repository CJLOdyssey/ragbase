export interface TeamMember {
  id: string;
  name: string;
  role: string;
  order: number;
  agentConfigId: string | null;
  systemPrompt: string | null;
  outputConstraints: string | null;
  tools: unknown[];
  mcp: unknown[];
  skills: unknown[];
}
