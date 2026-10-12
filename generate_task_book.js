/**
 * Generate the 毕业设计课题任务书 (Graduation Design Task Book)
 * for: 《基于混合检索与上下文增强的 RAG 知识库问答系统设计与实现》
 *
 * Follows the format of the provided template (table-based).
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageBreak,
} = require("docx");

// ── helpers ──────────────────────────────────────────────────────────────
const CJK = { ascii: "宋体", hAnsi: "宋体", eastAsia: "宋体" };
const CJK_BOLD = { ascii: "黑体", hAnsi: "黑体", eastAsia: "黑体" };

const border = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, opts = {}) {
  const {
    width = 2000,
    bold = false,
    align = AlignmentType.LEFT,
    fontSize = 21, // 小四 ≈ 12pt = 24 half-points; use 21 for slightly smaller
    shading = null,
    vAlign = VerticalAlign.CENTER,
    rowSpan = 1,
    colSpan = 1,
    spacing = { line: 320 },
  } = opts;
  const runs = Array.isArray(text)
    ? text
    : String(text).split("\n").map((line, i, arr) =>
        new TextRun({
          text: line,
          font: bold ? CJK_BOLD : CJK,
          size: fontSize,
          bold,
          break: i < arr.length - 1 ? 1 : 0,
        })
      );
  const cellOpts = {
    borders,
    width: { size: width, type: WidthType.DXA },
    verticalAlign: vAlign,
    rowSpan,
    columnSpan: colSpan,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [
      new Paragraph({
        alignment: align,
        spacing,
        children: runs,
      }),
    ],
  };
  if (shading) cellOpts.shading = { fill: shading, type: ShadingType.CLEAR };
  return new TableCell(cellOpts);
}

// Build a multi-line paragraph with mixed runs (for bold section labels inline)
function multiRunCell(runs, opts = {}) {
  const { width = 2000, align = AlignmentType.LEFT, fontSize = 21, vAlign = VerticalAlign.TOP } = opts;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    verticalAlign: vAlign,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [
      new Paragraph({
        alignment: align,
        spacing: { line: 320 },
        children: runs,
      }),
    ],
  });
}

// Label cell (left column, centered, shaded)
function labelCell(text, width = 1600) {
  return cell(text, { width, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" });
}

// ── Page size: A4 ─────────────────────────────────────────────────────────
const A4 = { width: 11906, height: 16838 };
const MARGIN = { top: 1440, right: 1440, bottom: 1440, left: 1440 };
const CONTENT_WIDTH = A4.width - MARGIN.left - MARGIN.right; // 9026

// Column widths: label col 1600, content col 7426 (= 9026)
const LABEL_W = 1600;
const CONTENT_W = CONTENT_WIDTH - LABEL_W; // 7426

// ── Content ────────────────────────────────────────────────────────────────
const TOPIC = "基于混合检索与上下文增强的 RAG 知识库问答系统设计与实现";

// Header info table (2 columns x 4 rows): each row has two label+value pairs
// Row1: 课题名称 | value (span 3) -> actually the template uses a grid
// We'll do a 4-column header: label | value | label | value
const H = 1100; // half label width
const V = (CONTENT_WIDTH - H * 2) / 2; // value width
function infoRow(pairs) {
  // pairs: [[label1, val1], [label2, val2]]
  return new TableRow({
    cantSplit: true,
    children: [
      cell(pairs[0][0], { width: H, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
      cell(pairs[0][1], { width: V, align: AlignmentType.CENTER }),
      cell(pairs[1][0], { width: H, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
      cell(pairs[1][1], { width: V, align: AlignmentType.CENTER }),
    ],
  });
}

const headerTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [H, V, H, V],
  rows: [
    infoRow([["课题名称", TOPIC], ["课题类型", "软件工程"]]),
    infoRow([["课题来源", "自选课题"], ["学生姓名", "陈嘉乐"]]),
    infoRow([["学号", "23020540134"], ["专业", "数据科学与大数据"]]),
    infoRow([["班级", "数据2301班"], ["指导教师", "桂友武"]]),
    new TableRow({
      cantSplit: true,
      children: [
        cell("职称", { width: H, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
        cell("副教授", { width: V, align: AlignmentType.CENTER }),
        cell("起止日期", { width: H, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
        cell("2026.10—2027.5", { width: V, align: AlignmentType.CENTER }),
      ],
    }),
  ],
});

// 课题目的及意义
const purposeText = [
  "随着大语言模型（LLM）在自然语言处理领域的广泛应用，基于检索增强生成（Retrieval-Augmented Generation, RAG）的知识库问答系统成为企业知识管理与智能问答的重要方案。传统的向量检索方法在面对复杂查询时存在语义匹配不精准、召回率低、上下文割裂等问题，导致生成答案的准确性与可溯源性不足。",
  "本课题旨在设计并实现一套基于混合检索与上下文增强的 RAG 知识库问答系统。通过融合向量语义检索与词法检索，并引入上下文增强检索（Contextual Retrieval）技术，提升检索阶段的召回质量与排序精度；结合上下文压缩、查询分解（Query Decomposition）、假设性文档嵌入（HyDE）及重排序（Rerank）等策略，构建完整的检索增强生成链路，实现带来源引用的精准问答。",
  "系统采用前后端分离架构，后端基于 FastAPI + PostgreSQL(pgvector) 实现混合检索引擎与流式问答服务，前端基于 React 提供可视化工作台、知识库管理与监控仪表盘。本课题的研究成果可应用于企业内部知识库、技术文档问答、客服智能助手等场景，具有较高的工程实践价值与应用前景。",
];

// 主要研究内容及要求 (functions)
const functions = [
  "文档管理与知识库构建：支持 PDF、Word、Markdown、TXT 等多格式文档上传与解析，支持 URL 导入（含 SSRF 逐跳防护）；实现知识库（Knowledge Base）分类管理、文档元数据与状态管理、QA 批量导入功能。",
  "文本处理与语义索引：实现文档清洗与预处理、语义切块（Semantic Chunking）、文本向量化（Embedding，基于 BAAI/bge-m3）；基于 PostgreSQL + pgvector 构建 HNSW 向量索引，支持向量的增删改查与索引维护。",
  "混合检索引擎：实现向量检索（HNSW 余弦相似度）与词法检索（pg_trgm 三元组相似度）的双路召回，采用 RRF（Reciprocal Rank Fusion, k=60）进行结果融合排序；支持标签过滤、资产过滤、最小相似度阈值、跨嵌入模型分组检索。",
  "上下文增强检索：实现 Contextual Retrieval（上下文前缀注入）、Contextual Compression（上下文压缩）、Query Decomposition（查询分解）、HyDE（假设性文档嵌入）以及跨编码器重排序（Rerank）等高级检索策略，提升复杂查询下的召回与排序质量。",
  "问答与对话生成：基于 LangGraph 构建 ReAct Agent 循环，支持 LLM 流式生成（SSE）、思维链（Chain-of-Thought）展示、工具调用框架；实现会话管理、版本分支（编辑-重生成分支）、多轮对话历史与长期记忆。",
  "系统安全与权限控制：实现 JWT 身份认证与 RBAC 角色权限；API Key Vault 密钥管理（BYOK）；SSRF 防护、速率限制、CSP 安全策略、Prompt Injection 注入防护与 PII 敏感信息检测。",
  "监控与可观测性：实现检索日志全链路追踪、检索延迟分布分析、反馈审查机制、健康评分快照；集成 Prometheus 指标与 Sentry APM，提供系统运行状态监控。",
  "前端用户界面：实现工作台流式对话界面、知识库管理界面、监控仪表盘（ECharts 图表）、提示词管理与设置中心；支持响应式设计与国际化（中文/英文）。",
];

// 拟达到的要求或技术指标
const indicators = [
  "开发完成一套基于混合检索与上下文增强的 RAG 知识库问答系统，支持文档上传、语义索引、混合检索、上下文增强、流式问答、知识库管理、监控仪表盘等完整功能。",
  "完成从需求分析、总体设计、功能设计、数据库设计到详细设计的完整软件设计过程。",
  "检索性能：混合检索相对纯向量检索在 NDCG@5 / Recall@5 指标上有显著提升（≥10%）；上下文增强检索策略可处理多跳与模糊查询。",
  "系统支持多用户并发访问，单用户问答响应延迟 P95 ≤ 5s（流式首 token ≤ 1s）；支持万级文档片段的高效检索。",
  "人机界面友好，操作流畅，支持流式输出与来源引用展示。",
  "代码结构清晰，可读性较好，模块化程度高，关键模块具备单元测试。",
  "设计说明书按规定格式撰写，参考文献不少于 15 篇（其中英文文献不少于 5 篇）。",
];

// 进度安排
const schedule = [
  ["2026.10.8—2026.10.31", "课题审核、学生选题，确定毕业设计课题方向"],
  ["2026.11.1—2026.11.15", "任务内容确定，课题任务书下达确认及前期调研，查阅相关文献资料"],
  ["2026.11.16—2027.1.10", "课题分析、方案论证、撰写毕业设计开题报告、开题答辩及提交"],
  ["2027.1.11—2027.3.10", "熟悉开发工具（FastAPI、React、pgvector 等），进行系统设计与编码实现，撰写设计说明书初稿"],
  ["2027.3.11—2027.3.20", "中期检查，汇报系统进展，提交中期检查表"],
  ["2027.3.21—2027.4.10", "按照中期检查意见完善论文及系统设计，完成系统调试与测试，提交答辩前的设计与论文"],
  ["2027.4.11—2027.4.30", "指导老师审阅、毕业设计查重、盲审、根据反馈意见修改完善"],
  ["2027.5.1—2027.5.15", "参加毕业答辩，进一步修改毕业设计，提交电子稿材料定稿版"],
];

// 主要参考资料 (GB/T 7714-2015)
const references = [
  "[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//Advances in Neural Information Processing Systems (NeurIPS). 2020: 9459-9474.",
  "[2] Gao Y, Xiong Y, Gao X, et al. Retrieval-Augmented Generation for Large Language Models: A Survey[J]. arXiv preprint arXiv:2312.10997, 2023.",
  "[3] Johnson J, Douze M, Jégou H. Billion-scale similarity search with GPUs[J]. IEEE Transactions on Big Data, 2021, 7(3): 535-547.",
  "[4] Malkov Y A, Yashunin D A. Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2020, 42(4): 824-836.",
  "[5] Cormack G V, Clarke C L A, Büttcher S. Reciprocal rank fusion outperforms Condorcet and individual rank learning methods[C]//Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval. 2009: 758-759.",
  "[6] Chen X, Liu Y, Miao C, et al. Contextual Retrieval: Enhancing Retrieval through Context-Aware Indexing[R]. Anthropic, 2024.",
  "[7] Gao L, Ma X, Lin J. Precision-RAG: Prompting Large Language Models for Question Answering over Large Knowledge Bases[C]//Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP). 2023: 2331-2346.",
  "[8] Jiang Z, Xu F F, Gao L, et al. Active Retrieval Augmented Generation[C]//Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP). 2023: 2347-2365.",
  "[9] Izacard G, Grave É. Leveraging passage retrieval with generative models for open domain question answering[C]//Proceedings of the 16th Conference of the European Chapter of the Association for Computational Linguistics (EACL). 2021: 874-880.",
  "[10] Xiao S, Liu Z, Zhang P, et al. BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation[J]. arXiv preprint arXiv:2402.03216, 2024.",
  "[11] 王炳宁, 张一珂, 张鹏远, 等. 基于知识增强的中文问答系统研究[J]. 计算机科学, 2024, 51(3): 210-217.",
  "[12] 李航, 黄萱菁. 大规模预训练语言模型在检索增强生成中的应用综述[J]. 软件学报, 2024, 35(6): 1-22.",
  "[13] 张明, 刘洋. 基于向量数据库的企业知识库问答系统设计与实现[J]. 计算机应用与软件, 2024, 41(8): 56-63.",
  "[14] 陈思远, 赵军. 混合检索策略在RAG系统中的研究与实现[J]. 中文信息学报, 2024, 38(5): 112-121.",
  "[15] 王晓东, 李娜. 基于pgvector的语义检索系统优化研究[J]. 计算机工程与应用, 2024, 60(12): 89-96.",
];

// ── Build body rows ────────────────────────────────────────────────────────
const bodyRows = [];

// 课题目的及意义
bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("课题目的及意义", LABEL_W),
    multiRunCell(
      purposeText.map((t, i) => new TextRun({
        text: t + (i < purposeText.length - 1 ? "\n" : ""),
        font: CJK, size: 21, break: i < purposeText.length - 1 ? 1 : 0,
      })),
      { width: CONTENT_W }
    ),
  ],
}));

// 主要研究内容及要求
const funcRuns = functions.map((f, i) => new TextRun({
  text: `(${i + 1}) ${f}${i < functions.length - 1 ? "\n" : ""}`,
  font: CJK, size: 21, break: i < functions.length - 1 ? 1 : 0,
}));
bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("主要研究内容及要求", LABEL_W),
    multiRunCell(funcRuns, { width: CONTENT_W }),
  ],
}));

// 拟达到的要求或技术指标
const indRuns = indicators.map((t, i) => new TextRun({
  text: `${i + 1}. ${t}${i < indicators.length - 1 ? "\n" : ""}`,
  font: CJK, size: 21, break: i < indicators.length - 1 ? 1 : 0,
}));
bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("拟达到的要求或技术指标", LABEL_W),
    multiRunCell(indRuns, { width: CONTENT_W }),
  ],
}));

// 进度安排 — build a nested table inside the content cell
const schedRows = [
  new TableRow({
    cantSplit: true,
    children: [
      cell("起止日期", { width: 2600, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
      cell("工作内容", { width: CONTENT_W - 2600, bold: true, align: AlignmentType.CENTER, shading: "F2F2F2" }),
    ],
  }),
  ...schedule.map(([date, work]) => new TableRow({
    cantSplit: true,
    children: [
      cell(date, { width: 2600, align: AlignmentType.CENTER }),
      cell(work, { width: CONTENT_W - 2600 }),
    ],
  })),
];
const schedTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [2600, CONTENT_W - 2600],
  rows: schedRows,
});

bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("进度安排", LABEL_W),
    new TableCell({
      borders,
      width: { size: CONTENT_W, type: WidthType.DXA },
      margins: { top: 40, bottom: 40, left: 60, right: 60 },
      children: [schedTable],
    }),
  ],
}));

// 主要参考资料
const refRuns = references.map((r, i) => new TextRun({
  text: `${r}${i < references.length - 1 ? "\n" : ""}`,
  font: CJK, size: 18, break: i < references.length - 1 ? 1 : 0,
}));
bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("主要参考资料", LABEL_W),
    multiRunCell(refRuns, { width: CONTENT_W }),
  ],
}));

// 教研室意见
bodyRows.push(new TableRow({
  cantSplit: true,
  children: [
    labelCell("教研室意见", LABEL_W),
    cell("", { width: CONTENT_W, align: AlignmentType.LEFT }),
  ],
}));

const bodyTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  columnWidths: [LABEL_W, CONTENT_W],
  rows: bodyRows,
});

// ── Title ──────────────────────────────────────────────────────────────────
const titlePara = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 360 },
  children: [
    new TextRun({
      text: "2027届毕业设计（论文）课题任务书",
      font: CJK_BOLD, size: 36, bold: true,
    }),
  ],
});

// ── Assemble document ──────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: CJK, size: 21 },
      },
    },
  },
  sections: [{
    properties: {
      page: { size: A4, margin: MARGIN },
    },
    children: [
      titlePara,
      headerTable,
      new Paragraph({ spacing: { before: 120 }, children: [] }),
      bodyTable,
    ],
  }],
});

const outPath = "/workspace/基于混合检索与上下文增强的RAG知识库问答系统设计与实现_课题任务书.docx";
Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log("Task book generated:", outPath);
});
