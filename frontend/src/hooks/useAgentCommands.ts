import { useMemo } from 'react';
import type { Team } from '../types/AgentStudio';
import type { CommandOption } from '../types/input';

/**
 * Derives slash commands from team agents' enabled MCP servers and skills.
 *
 * Each enabled MCP server becomes a command prefixed with the agent role.
 * Each enabled skill becomes a command.
 *
 * Example output:
 *   /github:search-code   (frontend agent's GitHub MCP)
 *   /slack:post-message   (pm agent's Slack MCP)
 *   /code-review          (architect agent's skill)
 */
export function useAgentCommands(teams: Team[]): CommandOption[] {
  return useMemo(() => {
    const commands: CommandOption[] = [];
    const seen = new Set<string>();

    for (const team of teams) {
      for (const agent of team.agents) {
        // Agent's enabled MCP servers → commands
        if (agent.mcp) {
          for (const mcp of agent.mcp) {
            if (!mcp.enabled) continue;
            const id = `mcp:${mcp.id}`;
            if (seen.has(id)) continue;
            seen.add(id);
            commands.push({
              id,
              name: mcp.name,
              description: `${agent.name} · ${mcp.serverUrl}`,
              source: 'agent',
            });
          }
        }

        // Agent's enabled skills → commands
        if (agent.skills) {
          for (const skill of agent.skills) {
            if (!skill.enabled) continue;
            const id = `skill:${skill.id}`;
            if (seen.has(id)) continue;
            seen.add(id);
            commands.push({
              id,
              name: skill.name,
              description: `${agent.name} · ${skill.description}`,
              source: 'agent',
            });
          }
        }

        // Agent's enabled tools → commands
        if (agent.tools) {
          for (const tool of agent.tools) {
            if (!tool.enabled) continue;
            const id = `tool:${tool.id}`;
            if (seen.has(id)) continue;
            seen.add(id);
            commands.push({
              id,
              name: tool.name,
              description: `${agent.name} · ${tool.description}`,
              source: 'agent',
            });
          }
        }
      }
    }

    return commands;
  }, [teams]);
}
