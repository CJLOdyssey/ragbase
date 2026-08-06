const MAX_INPUT_LENGTH = 10000;

// eslint-disable-next-line no-control-regex
const CONTROL_CHARS = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;

/** 团队名 / Agent 名最大长度 */
const MAX_NAME_LENGTH = 64;

/** 团队数量上限 */
const MAX_TEAMS = 50;

/** 每团队 Agent 数量上限 */
const MAX_AGENTS_PER_TEAM = 20;

/** 系统保留名称（不允许用户手动使用） */
const RESERVED_NAMES = ['新建', '默认', 'new', 'default'];

/** 危险字符（XSS 风险） */
const DANGEROUS_CHARS = /[<>&"'/]/;

export function validateInput(input: string): {
  valid: boolean;
  sanitized: string;
  error?: string;
} {
  const trimmed = input.trim();
  if (!trimmed)
    return { valid: false, sanitized: '', error: 'Input cannot be empty' };
  if (trimmed.length > MAX_INPUT_LENGTH) {
    return {
      valid: false,
      sanitized: '',
      error: `Input too long (max ${MAX_INPUT_LENGTH} characters)`,
    };
  }
  const sanitized = trimmed.replace(CONTROL_CHARS, '');
  return { valid: true, sanitized };
}

/**
 * 验证团队或 Agent 名称
 * @param name - 输入的名称
 * @param existingNames - 同级已存在的名称列表（用于查重）
 * @param excludeId - 排除自身 ID（编辑时排除自己）
 * @returns 验证结果
 */
export function validateName(
  name: string,
  existingNames: string[] = [],
  excludeId?: string,
): { valid: boolean; error?: string } {
  // 1. 空名检查
  const trimmed = name.trim();
  if (!trimmed) {
    return { valid: false, error: '名称不能为空' };
  }

  // 2. 长度检查
  if (trimmed.length > MAX_NAME_LENGTH) {
    return { valid: false, error: `名称不能超过 ${MAX_NAME_LENGTH} 个字符` };
  }

  if (trimmed.length < 1) {
    return { valid: false, error: '名称至少需要 1 个字符' };
  }

  // 3. 特殊字符检查（XSS 防护）
  if (DANGEROUS_CHARS.test(trimmed)) {
    return { valid: false, error: '名称包含非法字符 (< > & " \' /)' };
  }

  // 4. 保留字检查
  if (RESERVED_NAMES.includes(trimmed)) {
    return { valid: false, error: `"${trimmed}" 是系统保留名称` };
  }

  // 5. 去重检查（大小写不敏感）
  const normalized = trimmed.toLowerCase();
  const duplicates = existingNames.filter(
    (n) => n.toLowerCase() === normalized,
  );
  if (duplicates.length > 0) {
    // 编辑模式下，如果只有一个重复且就是自己本身，则允许
    if (excludeId && duplicates.length === 1) {
      return { valid: true };
    }
    return { valid: false, error: '名称已存在，请使用其他名称' };
  }

  return { valid: true };
}

/**
 * 检查团队数量是否超限
 */
export function checkTeamLimit(teamCount: number): {
  valid: boolean;
  error?: string;
} {
  if (teamCount >= MAX_TEAMS) {
    return { valid: false, error: `最多只能创建 ${MAX_TEAMS} 个团队` };
  }
  return { valid: true };
}

/**
 * 检查每团队 Agent 数量是否超限
 */
export function checkAgentLimit(agentCount: number): {
  valid: boolean;
  error?: string;
} {
  if (agentCount >= MAX_AGENTS_PER_TEAM) {
    return {
      valid: false,
      error: `每个团队最多 ${MAX_AGENTS_PER_TEAM} 个 Agent`,
    };
  }
  return { valid: true };
}

export function sanitizeMessageContent(content: string): string {
  return content.replace(CONTROL_CHARS, '');
}
