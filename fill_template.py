"""直接在模板上填充内容，保留原有表格结构。"""
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from copy import deepcopy

TEMPLATE = "/workspace/.uploads/6e796e02-7a00-4cac-bea7-d37e0d997204_2027届毕业设计课题任务书参考1 课题任务书_学号_姓名_软件工程2201班.docx"
OUTPUT = "/workspace/基于混合检索与上下文增强的RAG知识库问答系统设计与实现_课题任务书.docx"

doc = Document(TEMPLATE)

# --- 辅助：移除段落的自动列表编号 (numPr) ---
def remove_numpr(para_element):
    pPr = para_element.find(qn('w:pPr'))
    if pPr is not None:
        numPr = pPr.find(qn('w:numPr'))
        if numPr is not None:
            pPr.remove(numPr)

# --- 辅助：允许表格行跨页拆分（移除 cantSplit）---
def allow_row_split(row):
    trPr = row._tr.find(qn('w:trPr'))
    if trPr is not None:
        cantSplit = trPr.find(qn('w:cantSplit'))
        if cantSplit is not None:
            trPr.remove(cantSplit)

# --- 辅助：清空段落所有 run，设置文本 ---
def set_para_text(para, text):
    remove_numpr(para._element)
    # 保留第一个 run 的格式，删除其余
    for run in para.runs[1:]:
        run._element.getparent().remove(run._element)
    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)

# --- 辅助：清空单元格内容并写入多段文本 ---
def set_cell_text(cell, lines):
    # 删除除第一段外的所有段落
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    # 清空第一段内容
    first = cell.paragraphs[0]
    set_para_text(first, lines[0] if lines else "")
    # 添加后续段落，复制第一段格式
    prev = first._element
    for line in lines[1:]:
        new_p = deepcopy(first._element)
        remove_numpr(new_p)
        # 清空 new_p 的 run 文本
        for r in new_p.findall(qn('w:r')):
            t = r.find(qn('w:t'))
            if t is not None:
                t.text = ""
        # 找到第一个 run 设置文本
        runs = new_p.findall(qn('w:r'))
        if runs:
            t = runs[0].find(qn('w:t'))
            if t is not None:
                t.text = line
        prev.addnext(new_p)
        prev = new_p

# ============================================================
# 1. 学院/专业 行（表格外的段落）
# ============================================================
for para in doc.paragraphs:
    if "学院：计算机科学与工程学院" in para.text and "专业" in para.text:
        set_para_text(para, "学院：计算机科学与工程学院               专业：数据科学与大数据")
        break

# ============================================================
# 2. 主表格填充
# ============================================================
table = doc.tables[0]

# --- 行0：表头信息行（指导教师 | 值 | 学生姓名 | 值 | 课题名称 | 值）---
# 实际是 5 列结构：[指导教师][值][学生姓名][值][课题名称/值]
# 根据模板，这一行包含 指导教师、学生姓名、课题名称 及其值
row0 = table.rows[0]
cells0 = row0.cells
# 遍历找到包含关键字的单元格并设置对应值
texts0 = [c.text.strip() for c in cells0]
print("Row0 cells:", texts0)

# 打印所有行结构以便调试
for ri, row in enumerate(table.rows):
    print(f"Row {ri}: {[c.text[:30] for c in row.cells]}")

# Row 0: 指导教师(合并) | 值 | 学生姓名 | 值
set_cell_text(cells0[2], ["桂友武"])
set_cell_text(cells0[4], ["陈嘉乐"])

# Row 1: 课题名称(合并) | 值(合并 3 列)
row1 = table.rows[1]
set_cell_text(row1.cells[2], ["基于混合检索与上下文增强的 RAG 知识库问答系统设计与实现"])

# --- 后续行：找到包含"内容及任务"、"拟达到的要求"、"进度安排"、"主要参考资料"、"教研室意见"的行 ---
content_task = None
requirement = None
schedule = None
references = None
office_opinion = None

for row in table.rows:
    txt = "".join(c.text for c in row.cells)
    if "内容及任务" in txt and content_task is None:
        content_task = row
    elif "拟达到的要求" in txt and requirement is None:
        requirement = row
    elif "进度安排" in txt and schedule is None:
        schedule = row
    elif "主要参考资料" in txt and references is None:
        references = row
    elif "教研室" in txt and office_opinion is None:
        office_opinion = row

print("Found sections:",
      "内容及任务" if content_task else "MISSING",
      "| 拟达到的要求" if requirement else "| MISSING req",
      "| 进度安排" if schedule else "| MISSING sch",
      "| 主要参考资料" if references else "| MISSING ref",
      "| 教研室意见" if office_opinion else "| MISSING office")

# --- 内容及任务 (Row 2) ---
if content_task:
    cell = content_task.cells[1]  # cell[0] 是标签"内容及任务"，cells[1-4] 合并为值
    lines = [
        "综合运用在学期间所学数据科学与大数据专业知识和技能，设计开发基于混合检索与上下文增强的 RAG 知识库问答系统，掌握计算机领域项目开发的基本流程，检验学生的学习效果和动手能力，提高学生工程实践能力，为将来实际工作打下坚实的基础。",
        "本课题的既定目标是构建一个支持文档上传、语义索引、混合检索、上下文增强和问答生成的知识库问答平台。开展文献调研与需求分析，提出系统总体方案，设计与实现文档管理、语义索引、混合检索、上下文增强、问答生成等模块，并完成项目相应的测试、优化及文档撰写。本项目一般应包含如下功能：",
        "（1）文档管理模块：支持多种格式文档的上传、解析、分段与存储；",
        "（2）语义索引模块：对文档片段进行向量化表示，建立高效的向量索引与词法索引；",
        "（3）混合检索模块：实现向量检索与关键词检索的混合召回，融合多路检索结果并进行重排序；",
        "（4）上下文增强模块：对文档片段补充上下文信息，结合查询改写等技术提升检索精度；",
        "（5）问答生成模块：基于大语言模型构建智能问答引擎，支持流式输出、来源引用与多轮对话；",
        "（6）系统管理模块：包含用户认证、权限控制、密钥管理、检索日志与监控功能。",
    ]
    set_cell_text(cell, lines)
    allow_row_split(content_task)

# --- 拟达到的要求或技术指标 (Row 3) ---
if requirement:
    cell = requirement.cells[1]
    lines = [
        "1、开发基于混合检索与上下文增强的 RAG 知识库问答系统，支持文档上传、语义索引、混合检索、上下文增强和问答功能；",
        "2、完成从需求分析、总体设计、功能设计、数据库设计到详细设计的完整软件设计过程；",
        "3、混合检索相比单一检索方式在检索准确率上有明显提升；",
        "4、问答响应速度满足实际使用需求，支持流式输出；",
        "5、支持大规模文档片段的高效检索与管理；",
        "6、人机界面友好，代码可读性较好，设计说明书按规定格式书写。",
        "开发工具：VS Code。",
        "开发环境：Python 3.12、Node.js 22。",
        "开发语言：Python、TypeScript。",
        "采用技术：FastAPI、React、PostgreSQL、pgvector、Redis、Celery、LangGraph、BGE-M3。",
    ]
    set_cell_text(cell, lines)
    allow_row_split(requirement)

# --- 进度安排 (Row 4) ---
if schedule:
    cell = schedule.cells[1]
    lines = [
        "2026.10.8-2026.10.31  课题审核、学生选题",
        "2026.11.1-2026.11.20  任务内容确定，课题任务书的下达确认及前期调研",
        "2026.11.21-2027.1.20  课题分析、方案论证、撰写毕业设计开题报告、答辩及提交",
        "2027.1.21-2027.3.29  熟悉开发工具，进行系统设计与实现，撰写设计说明书初稿",
        "2027.3.30-2027.4.5  中期检查",
        "2027.4.6-2027.4.22  按照中期检查完善论文及设计，提交答辩前的设计与论文",
        "2027.4.23-2027.5.31  指导老师审阅、毕业设计查重、盲审、修改",
        "2027.6.1-2027.6.7  参加毕业答辩，进一步修改毕业设计，提交电子稿材料定稿版",
    ]
    set_cell_text(cell, lines)
    allow_row_split(schedule)

# --- 主要参考资料 (Row 5) ---
if references:
    cell = references.cells[1]
    lines = [
        "[1] 王鑫林, 李岩, 马超凡, 等. 检索增强生成综述：方法与应用[J]. 计算机科学, 2026, 53(07): 101-117.",
        "[2] 吴海周, 黄俊, 张佳晨. 基于RAG机制的知识库问答性能优化与参数调控研究[J]. 工业控制计算机, 2026, 39(07): 111-113.",
        "[3] 高川, 王龙刚, 朱晓蕾, 等. 云端―本地双模式私有知识库RAG问答系统设计与实现[J]. 计算机时代, 2026(09): 104-109.",
        "[4] 李俊奇, 李子林, 王跃, 等. 基于检索增强与知识库融合的铁科智问系统设计与实现[J]. 铁路计算机应用, 2026, 35(05): 42-45.",
        "[5] 张墨涵. 融合检索增强的企业私有知识库智能问答系统[J]. 中国新技术新产品, 2026.",
        "[6] 裴丽娜, 淦欣喆, 陈明, 等. 基于领域HyDE查询增强与LightRAG的水稻种植检索增强生成方法[J]. 智慧农业(中英文), 2026.",
        "[7] 马成业, 马满堂. 面向大语言模型智能体的查询反馈驱动上下文蒸馏方法[J]. 计算机工程与应用, 2026.",
        "[8] 张凯, 满广垠, 叶治荣. 基于混合RAG的铁路工程规范智能问答方法研究[J]. 中国铁路, 2026.",
        "[9] 王亮, 张强, 魏韵萧. 基于知识库的智能问答系统构建技术研究[J]. 网络安全与数据治理, 2026.",
        "[10] 彭琳. 基于检索增强生成的企业级知识库系统构建与优化[J]. 电脑知识与技术, 2026.",
        "[11] 吕志锦. 基于知识图谱和大语言模型的垂直领域问答系统的设计与实现[D]. 北京: 北京邮电大学, 2025.",
        "[12] 何一苇. 基于大模型的客服知识库问答系统的设计与实现[D]. 北京: 北京邮电大学, 2025.",
        "[13] 周青青. 基于检索增强生成的胃病智能问答系统设计与实现[D]. 合肥: 安徽中医药大学, 2025.",
        "[14] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//Advances in Neural Information Processing Systems. 2020: 9459-9474.",
        "[15] Gao Y, Xiong Y, Gao X, et al. Retrieval-Augmented Generation for Large Language Models: A Survey[J]. arXiv preprint arXiv:2312.10997, 2023.",
        "[16] Malkov Y A, Yashunin D A. Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2020, 42(4): 824-836.",
        "[17] Cormack G V, Clarke C L A, Buettcher S. Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods[C]//Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval. 2009: 758-759.",
        "[18] Jiang Z, Yan J, Wang S, et al. FLARE: Active Retrieval Augmented Generation[C]//Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing. 2023: 2118-2132.",
    ]
    set_cell_text(cell, lines)
    allow_row_split(references)

# --- 教研室意见：保留原样，不动 ---

doc.save(OUTPUT)
print(f"\nSaved: {OUTPUT}")
